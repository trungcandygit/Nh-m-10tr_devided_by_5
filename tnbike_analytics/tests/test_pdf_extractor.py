"""
Tests cho pdf_extractor.py — dùng file thực tế BH26_1132.pdf
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PDF_DIR    = Path("/root/tnbike_workspace/my_data/tnbike_pdfs_mar2026")
SAMPLE_PDF = PDF_DIR / "BH26_1132.pdf"


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="File mẫu không có")
def test_extract_so_chung_tu():
    from pipeline.pdf_extractor import extract_from_file
    doc = extract_from_file(SAMPLE_PDF)
    assert doc.so_chung_tu == "BH26.1132", f"Expected BH26.1132, got {doc.so_chung_tu}"


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="File mẫu không có")
def test_extract_ngay_dat():
    from pipeline.pdf_extractor import extract_from_file
    doc = extract_from_file(SAMPLE_PDF)
    assert "2026" in doc.ngay_dat, f"Ngày không có 2026: {doc.ngay_dat}"
    assert "3" in doc.ngay_dat or "03" in doc.ngay_dat, f"Ngày không phải T3: {doc.ngay_dat}"


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="File mẫu không có")
def test_extract_mst():
    from pipeline.pdf_extractor import extract_from_file
    doc = extract_from_file(SAMPLE_PDF)
    assert doc.mst == "156553168", f"MST sai: {doc.mst}"


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="File mẫu không có")
def test_extract_lines():
    from pipeline.pdf_extractor import extract_from_file
    doc = extract_from_file(SAMPLE_PDF)
    assert len(doc.lines) > 0, "Không parse được dòng sản phẩm nào"
    # Kiểm tra dòng đầu tiên
    first = doc.lines[0]
    assert first.ma_hang != "", "Mã hàng rỗng"
    assert first.so_luong > 0, "Số lượng <= 0"
    assert first.don_gia > 0, "Đơn giá <= 0"


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="File mẫu không có")
def test_total_consistency():
    from pipeline.pdf_extractor import extract_from_file
    doc = extract_from_file(SAMPLE_PDF)
    sum_lines = sum(l.thanh_tien for l in doc.lines)
    if doc.tong_gia_tri > 0:
        diff_pct = abs(sum_lines - doc.tong_gia_tri) / doc.tong_gia_tri
        assert diff_pct < 0.05, f"Tổng lệch {diff_pct:.1%}: sum={sum_lines}, footer={doc.tong_gia_tri}"


def test_clean_number():
    from pipeline.pdf_extractor import _clean_number
    assert _clean_number("1.616.111") == 1616111.0
    assert _clean_number("8.080.555") == 8080555.0
    assert _clean_number("0")         == 0.0
    assert _clean_number("")          == 0.0
