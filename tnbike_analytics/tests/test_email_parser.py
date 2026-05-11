"""
Tests cho email_parser.py — dùng file thực tế BH26_1132.eml
"""
import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

EMAIL_DIR = Path("/root/tnbike_workspace/my_data/tnbike_emails_mar2026")
SAMPLE_EML = EMAIL_DIR / "BH26_1132.eml"


@pytest.mark.skipif(not SAMPLE_EML.exists(), reason="File mẫu không có")
def test_parse_eml_basic():
    from pipeline.email_parser import parse_eml
    ed = parse_eml(SAMPLE_EML)
    assert ed.error is None, f"Parse lỗi: {ed.error}"
    assert "BH26" in ed.subject or "BH26" in ed.so_number_body
    assert ed.from_address != ""
    assert len(ed.attachment_bytes) > 0, "Không có PDF attachment"


@pytest.mark.skipif(not SAMPLE_EML.exists(), reason="File mẫu không có")
def test_parse_eml_body_fields():
    from pipeline.email_parser import parse_eml
    ed = parse_eml(SAMPLE_EML)
    # MST phải là chuỗi số
    if ed.mst_body:
        assert ed.mst_body.isdigit()
    # Ngày phải có dấu /
    if ed.order_date_body:
        assert "/" in ed.order_date_body or "-" in ed.order_date_body


def test_parse_eml_empty_file(tmp_path):
    from pipeline.email_parser import parse_eml
    f = tmp_path / "empty.eml"
    f.write_bytes(b"")
    ed = parse_eml(f)
    assert ed.error is not None


def test_parse_all_emails_count():
    from pipeline.email_parser import parse_all_emails
    if not EMAIL_DIR.exists():
        pytest.skip("Email dir không có")
    results = parse_all_emails(EMAIL_DIR)
    # Có tổng 1132 file; 1 số file rỗng → số parse được phải > 0
    non_empty = [r for r in results if not r.error]
    assert len(non_empty) > 0
