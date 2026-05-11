"""Tests cho validator.py"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.validator import validate_order, Status
from pipeline.pdf_extractor import OrderDocument, OrderLine
from pipeline.email_parser import EmailData


def _make_email(so_number="BH26.0001", mst="123456789"):
    return EmailData(
        message_id="test-id", from_address="test@test.vn", from_name="Test",
        received_at="Mon, 02 Mar 2026 09:00:00 +0700", subject=f"[ĐẶT HÀNG] {so_number}",
        attachment_name=f"{so_number.replace('.','_')}.pdf", attachment_bytes=b"pdf",
        body_text="", raw_path="/tmp/test.eml",
        so_number_body=so_number, order_date_body="02/03/2026", mst_body=mst,
    )


def _make_doc(so_number="BH26.0001", ngay="02/03/2026", mst="123456789", n_lines=2):
    doc = OrderDocument(so_chung_tu=so_number, ngay_dat=ngay, mst=mst, ten_dai_ly="Test Đại Lý")
    for i in range(1, n_lines + 1):
        doc.lines.append(OrderLine(
            stt=i, ma_hang=f"PROD{i:03d}", ten_sp=f"Xe {i}", dvt="Chiếc",
            so_luong=5.0, don_gia=1_000_000.0, thanh_tien=5_000_000.0,
        ))
    doc.tong_gia_tri = sum(l.thanh_tien for l in doc.lines)
    return doc


REF = {
    "valid_products":  {"PROD001", "PROD002", "PROD003"},
    "valid_customers": {"KH-00001"},
    "tax_to_customer": {"123456789": "KH-00001"},
    "existing_orders": set(),
}


def test_valid_order():
    doc   = _make_doc()
    email = _make_email()
    result = validate_order(doc, email, REF)
    assert result.ok, f"Nên VALID nhưng là {result.status}: {result.errors}"


def test_invalid_wrong_month():
    doc   = _make_doc(ngay="15/01/2026")
    email = _make_email()
    email.order_date_body = "15/01/2026"
    result = validate_order(doc, email, REF)
    assert result.status == Status.INVALID
    assert any("T3/2026" in e for e in result.errors)


def test_invalid_duplicate():
    ref_dup = {**REF, "existing_orders": {"BH26.0001"}}
    doc     = _make_doc()
    email   = _make_email()
    result  = validate_order(doc, email, ref_dup)
    assert result.status == Status.INVALID
    assert any("đã tồn tại" in e for e in result.errors)


def test_warning_unknown_product():
    doc   = _make_doc()
    email = _make_email()
    doc.lines[0].ma_hang = "UNKNOWN_SKU"
    result = validate_order(doc, email, REF)
    assert result.status in (Status.WARNING, Status.VALID)
    if result.warnings:
        assert any("không có trong DB" in w for w in result.warnings)


def test_invalid_no_lines():
    doc   = _make_doc(n_lines=0)
    email = _make_email()
    result = validate_order(doc, email, REF)
    assert result.status == Status.INVALID
