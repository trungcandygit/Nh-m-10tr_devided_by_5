"""
Entry point Pipeline A — Xử lý 1.132 email/PDF đặt hàng T3/2026
Chạy: python -m pipeline.run_pipeline --email-dir data/raw/emails --pdf-dir data/raw/pdfs
"""
import argparse
import json
import time
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/processed/pipeline.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("tnbike.pipeline")


def run(email_dir: Path, pdf_dir: Path) -> dict:
    from pipeline.email_parser  import parse_all_emails
    from pipeline.pdf_extractor import extract_from_bytes
    from pipeline.validator     import validate_order
    from pipeline.db_writer     import write_full_order, refresh_fact_sales
    from pipeline.db_connection import get_connection, load_reference_data
    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = lambda x, **kw: x  # noqa

    stats = {
        "bat_dau":       datetime.now().isoformat(),
        "tong_file":     0,
        "thanh_cong":    0,
        "loi_invalid":   0,
        "canh_bao":      0,
        "tong_don_hang": 0,
        "tong_dong_sp":  0,
        "danh_sach_loi": [],
        "_times":        [],
    }

    with get_connection() as conn:
        ref = load_reference_data(conn)

    emails = parse_all_emails(email_dir)
    stats["tong_file"] = len(emails)
    logger.info(f"Bắt đầu xử lý {len(emails)} email")

    for email_data in tqdm(emails, desc="Pipeline A", unit="email"):
        t0 = time.time()
        try:
            if email_data.error or not email_data.attachment_bytes:
                stats["loi_invalid"] += 1
                stats["danh_sach_loi"].append({
                    "file": email_data.raw_path,
                    "loi":  email_data.error or "Không có PDF đính kèm",
                })
                continue

            order_doc = extract_from_bytes(email_data.attachment_bytes)
            if order_doc.error and not order_doc.lines:
                stats["loi_invalid"] += 1
                stats["danh_sach_loi"].append({
                    "file": email_data.raw_path,
                    "loi":  f"Lỗi parse PDF: {order_doc.error}",
                })
                continue

            result = validate_order(order_doc, email_data, ref)
            write_result = write_full_order(email_data, order_doc, result)

            if write_result["status"] == "OK":
                stats["thanh_cong"] += 1
                stats["tong_don_hang"] += 1
                stats["tong_dong_sp"]  += len(order_doc.lines)
                if result.warnings:
                    stats["canh_bao"] += 1
            else:
                stats["loi_invalid"] += 1
                stats["danh_sach_loi"].append({
                    "file": email_data.raw_path,
                    "loi":  "; ".join(result.errors),
                })

        except Exception as e:
            stats["loi_invalid"] += 1
            stats["danh_sach_loi"].append({"file": email_data.raw_path, "loi": str(e)})
            logger.error(f"Lỗi xử lý {email_data.raw_path}: {e}")

        stats["_times"].append(time.time() - t0)

    logger.info("Đang refresh fact_sales T3/2026...")
    try:
        refresh_fact_sales()
    except Exception as e:
        logger.error(f"Lỗi refresh fact_sales: {e}")

    times = stats.pop("_times")
    stats["thoi_gian_tb_giay"] = round(sum(times) / len(times), 3) if times else 0
    stats["ket_thuc"] = datetime.now().isoformat()

    out = Path("data/processed/pipeline_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=2))

    logger.info(
        f"Xong: {stats['thanh_cong']}/{stats['tong_file']} thành công | "
        f"Lỗi: {stats['loi_invalid']} | Cảnh báo: {stats['canh_bao']}"
    )
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline A — TNBike T3/2026")
    parser.add_argument("--email-dir", default="data/raw/emails")
    parser.add_argument("--pdf-dir",   default="data/raw/pdfs")
    args = parser.parse_args()
    run(Path(args.email_dir), Path(args.pdf_dir))
