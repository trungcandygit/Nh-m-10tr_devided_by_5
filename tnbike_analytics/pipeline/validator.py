"""
Kiểm tra tính hợp lệ đơn hàng trước khi ghi vào PostgreSQL
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger("tnbike.validator")


class Status(Enum):
    VALID   = "VALID"
    INVALID = "INVALID"
    WARNING = "WARNING"


@dataclass
class ValidationResult:
    status:   Status
    errors:   list
    warnings: list

    @property
    def ok(self) -> bool:
        return self.status in (Status.VALID, Status.WARNING)


def _parse_date(s: str) -> datetime:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Không nhận dạng ngày: {s}")


def validate_order(doc, email_data, ref: dict) -> ValidationResult:
    """
    Kiểm tra OrderDocument + EmailData trước khi ghi DB.

    Kiểm tra:
    1. MST → tra được customer_code trong customer table
    2. Ngày đặt hàng phải trong T3/2026
    3. Số chứng từ chưa tồn tại (chống duplicate)
    4. Ít nhất 1 dòng sản phẩm được parse
    5. Mỗi dòng: mã hàng hợp lệ, SL > 0, đơn giá > 0
    6. Thành tiền ≈ SL × đơn giá (sai lệch < 1%)
    7. Tổng dòng ≈ tổng footer (sai lệch < 1%)
    """
    errors, warnings = [], []

    # Resolve customer_code qua MST
    mst = doc.mst or email_data.mst_body
    customer_code = ref["tax_to_customer"].get(mst, "")
    if not mst:
        errors.append("Thiếu MST đại lý trong PDF")
    elif not customer_code:
        warnings.append(f"MST {mst} chưa có trong customer table — sẽ dùng email domain lookup")
    doc.ma_dai_ly = customer_code

    # Ngày đặt hàng
    ngay_dat = doc.ngay_dat or email_data.order_date_body
    if ngay_dat:
        try:
            d = _parse_date(ngay_dat)
            if not (d.year == 2026 and d.month == 3):
                errors.append(f"Ngày đặt không phải T3/2026: {ngay_dat}")
        except ValueError:
            warnings.append(f"Không parse được ngày: {ngay_dat}")
    else:
        warnings.append("Thiếu ngày đặt hàng")

    # So số — lấy từ PDF, fallback email body, fallback filename
    so_chung_tu = doc.so_chung_tu or email_data.so_number_body
    if not so_chung_tu:
        errors.append("Không tìm được số chứng từ")
    elif so_chung_tu in ref["existing_orders"]:
        errors.append(f"Đơn hàng đã tồn tại: {so_chung_tu}")
    doc.so_chung_tu = so_chung_tu

    # Dòng sản phẩm
    if not doc.lines:
        errors.append("Không trích xuất được dòng sản phẩm nào từ PDF")
    else:
        for i, line in enumerate(doc.lines, 1):
            if not line.ma_hang:
                errors.append(f"Dòng {i}: thiếu mã hàng")
                continue
            if line.ma_hang not in ref["valid_products"]:
                warnings.append(f"Dòng {i}: mã hàng không có trong DB: {line.ma_hang}")
            if line.so_luong <= 0:
                errors.append(f"Dòng {i}: số lượng không hợp lệ ({line.so_luong})")
            if line.don_gia <= 0:
                warnings.append(f"Dòng {i}: đơn giá = 0 ({line.ma_hang})")
            expected = line.so_luong * line.don_gia
            if expected > 0 and line.thanh_tien > 0:
                diff = abs(line.thanh_tien - expected) / expected
                if diff > 0.01:
                    warnings.append(
                        f"Dòng {i}: thành tiền lệch {diff:.1%} "
                        f"(expected {expected:,.0f}, got {line.thanh_tien:,.0f})"
                    )

    # Kiểm tra tổng footer
    sum_lines = sum(l.thanh_tien for l in doc.lines)
    if doc.tong_gia_tri > 0 and sum_lines > 0:
        diff = abs(sum_lines - doc.tong_gia_tri) / doc.tong_gia_tri
        if diff > 0.01:
            warnings.append(
                f"Tổng dòng ({sum_lines:,.0f}) lệch {diff:.1%} "
                f"so với footer ({doc.tong_gia_tri:,.0f})"
            )

    if errors:
        return ValidationResult(Status.INVALID, errors, warnings)
    elif warnings:
        return ValidationResult(Status.WARNING, [], warnings)
    return ValidationResult(Status.VALID, [], [])
