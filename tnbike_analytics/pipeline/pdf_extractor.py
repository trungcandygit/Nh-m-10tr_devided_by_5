"""
Trích xuất dữ liệu đơn hàng từ file PDF đặt hàng Thống Nhất
Layout thực tế (xem BH26_1132.pdf):
  Header: logo Xe đạp Thống Nhất, "ĐƠN ĐẶT HÀNG / PURCHASE ORDER"
  Trường: Số đơn hàng (BH26.XXXX) | Ngày | Đại lý | MST | Địa chỉ
  Bảng: STT | Mã hàng | Tên sản phẩm | ĐVT | SL | Đơn giá (đ) | Thành tiền (đ)
  Footer: Tổng: XX chiếc | Tổng giá trị: XX đồng (chưa VAT)
Dùng pdftotext (poppler-utils) vì pdfplumber/pypdf bị lỗi cffi.
"""
import subprocess
import re
import io
import tempfile
import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("tnbike.pdf_extractor")


@dataclass
class OrderLine:
    stt:          int
    ma_hang:      str
    ten_sp:       str
    dvt:          str
    so_luong:     float
    don_gia:      float
    thanh_tien:   float


@dataclass
class OrderDocument:
    so_chung_tu:  str
    ngay_dat:     str
    ma_dai_ly:    str = ""   # customer_code — tra cứu qua MST
    ten_dai_ly:   str = ""
    mst:          str = ""
    dia_chi:      str = ""
    lines:        list = field(default_factory=list)
    tong_so_luong: int = 0
    tong_gia_tri:  float = 0.0
    method:        str = "pdftotext"
    error:         Optional[str] = None


def _clean_number(s: str) -> float:
    """'1.616.111' hoặc '1,616,111' → 1616111.0"""
    if not s:
        return 0.0
    s = str(s).strip().replace("\xa0", "").replace(" ", "")
    # Định dạng Việt Nam: dấu chấm là phân cách hàng nghìn
    # Loại bỏ tất cả dấu chấm, dấu phẩy (không có số thập phân trong đơn giá xe đạp)
    s = re.sub(r'[.,]', '', s)
    try:
        return float(s)
    except ValueError:
        return 0.0


def _extract_text_pdftotext(pdf_bytes: bytes) -> str:
    """Dùng pdftotext (poppler) để lấy text từ PDF bytes."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", tmp_path, "-"],
            capture_output=True, timeout=30
        )
        text = result.stdout.decode("utf-8", errors="replace")
        return text
    finally:
        os.unlink(tmp_path)


def parse_order_text(text: str) -> OrderDocument:
    """
    Parse văn bản PDF đã được pdftotext trích xuất.
    Regex dựa trên layout thực tế của file BH26_1132.pdf.
    """
    doc = OrderDocument(so_chung_tu="", ngay_dat="")

    # Số đơn hàng
    m = re.search(r'(BH26\.\d+)', text)
    if m:
        doc.so_chung_tu = m.group(1)

    # Ngày
    m = re.search(r'Ng[àa]y\s*[:\s]+([\d]+/[\d]+/[\d]+)', text, re.IGNORECASE)
    if m:
        doc.ngay_dat = m.group(1).strip()

    # Đại lý (dòng sau "Đại lý:" hoặc "Đ■i lý:")
    m = re.search(r'[ĐD][■a]i\s*l[ýy]\s*[:\s]+(.+?)(?:\n|MST)', text, re.IGNORECASE | re.DOTALL)
    if m:
        doc.ten_dai_ly = m.group(1).strip().split("\n")[0].strip()

    # MST đại lý — tìm trên cùng dòng với "Đại lý" (không phải MST của Thống Nhất ở header)
    m = re.search(r'[■ĐD][■a]i\s*l[■ýy].+?MST\s*[:\s]+(\d{9,13})', text, re.IGNORECASE)
    if m:
        doc.mst = m.group(1).strip()
    else:
        # Fallback: lấy MST thứ 2 trong tài liệu (MST đầu là của Thống Nhất)
        all_mst = re.findall(r'MST\s*[:\s]+(\d{9,13})', text, re.IGNORECASE)
        if len(all_mst) >= 2:
            doc.mst = all_mst[1]
        elif len(all_mst) == 1:
            doc.mst = all_mst[0]

    # Địa chỉ
    m = re.search(r'[ĐD][■i][a-z]*\s*ch[■i][■]\s*[:\s]+(.+?)(?:\n\s*\n|\n[A-ZĐÁÂĂÊÔƠƯÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ])',
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        doc.dia_chi = " ".join(m.group(1).split()).strip()

    # Phân tích bảng sản phẩm
    # Tìm dòng có pattern: STT Mã_hàng Tên_sản_phẩm ĐVT SL Đơn_giá Thành_tiền
    # Ví dụ: "1  000225002002000  Xe đạp Thống Nhất New 26 Trắng  Chiếc  5  1.616.111  8.080.555"
    line_pattern = re.compile(
        r'^\s*(\d+)\s+'                          # STT
        r'(\S{10,20})\s+'                         # Mã hàng (10-20 ký tự không dấu cách)
        r'(.+?)\s+'                               # Tên sản phẩm
        r'(Chi[■ế]c|B[ộo]\s*\S+)\s+'            # ĐVT
        r'(\d+)\s+'                               # Số lượng
        r'([\d.,]+)\s+'                           # Đơn giá
        r'([\d.,]+)\s*$',                         # Thành tiền
        re.MULTILINE | re.IGNORECASE
    )

    for m in line_pattern.finditer(text):
        try:
            line = OrderLine(
                stt       = int(m.group(1)),
                ma_hang   = m.group(2).strip(),
                ten_sp    = m.group(3).strip(),
                dvt       = m.group(4).strip(),
                so_luong  = float(m.group(5)),
                don_gia   = _clean_number(m.group(6)),
                thanh_tien= _clean_number(m.group(7)),
            )
            if line.ma_hang and line.so_luong > 0:
                doc.lines.append(line)
        except Exception:
            pass

    # Nếu không parse được qua regex, thử parse từng dòng theo cột
    if not doc.lines:
        doc.lines = _parse_lines_fallback(text)

    # Tổng từ footer
    m_total = re.search(r'T[■ổ]ng\s*[:\s]*([\d.,]+)\s*chi[■ế]c', text, re.IGNORECASE)
    if m_total:
        doc.tong_so_luong = int(_clean_number(m_total.group(1)))

    m_value = re.search(
        r'T[■ổ]ng\s+gi[áa]\s+tr[■ị]\s+[■đ][■ơ]n\s+h[àa]ng\s*[:\s]*([\d.,]+)',
        text, re.IGNORECASE
    )
    if m_value:
        doc.tong_gia_tri = _clean_number(m_value.group(1))

    return doc


def _parse_lines_fallback(text: str) -> list:
    """
    Fallback: tìm dòng bắt đầu bằng số thứ tự theo định dạng cột cố định.
    pdftotext -layout giữ nguyên vị trí cột.
    """
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        # Bắt đầu bằng số (1-99) và có mã hàng dạng 15-16 chữ số
        m = re.match(
            r'^(\d{1,3})\s+([\d]{10,18})\s+(.+?)\s+Chi[■ế]c\s+(\d+)\s+([\d.,]+)\s+([\d.,]+)',
            line, re.IGNORECASE
        )
        if m:
            try:
                ol = OrderLine(
                    stt       = int(m.group(1)),
                    ma_hang   = m.group(2).strip(),
                    ten_sp    = m.group(3).strip(),
                    dvt       = "Chiếc",
                    so_luong  = float(m.group(4)),
                    don_gia   = _clean_number(m.group(5)),
                    thanh_tien= _clean_number(m.group(6)),
                )
                if ol.so_luong > 0:
                    lines.append(ol)
            except Exception:
                pass
    return lines


def extract_from_bytes(pdf_bytes: bytes) -> OrderDocument:
    """Trích xuất OrderDocument từ PDF bytes."""
    try:
        text = _extract_text_pdftotext(pdf_bytes)
        doc  = parse_order_text(text)
        return doc
    except Exception as e:
        doc = OrderDocument(so_chung_tu="", ngay_dat="", error=str(e))
        logger.warning(f"Lỗi extract PDF: {e}")
        return doc


def extract_from_file(pdf_path) -> OrderDocument:
    """Trích xuất từ file PDF trên disk."""
    from pathlib import Path
    return extract_from_bytes(Path(pdf_path).read_bytes())
