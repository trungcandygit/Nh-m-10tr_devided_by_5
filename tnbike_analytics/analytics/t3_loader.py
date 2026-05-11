"""
Đọc 1.132 email/PDF T3/2026 → DataFrame fact rows
Dùng pdftotext (không cần PostgreSQL).
"""
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd

logger = logging.getLogger("tnbike.t3_loader")

EMAIL_DIR = Path(__file__).parent.parent / "data" / "raw" / "emails"


def load_t3(dfs: dict, email_dir: Path = EMAIL_DIR) -> pd.DataFrame:
    """
    Parse toàn bộ .eml trong email_dir, join với reference tables từ dfs,
    trả về DataFrame cùng schema với build_fact().
    Chỉ nhận đơn ngày T3/2026. Bỏ qua đơn lỗi parse / ngày sai.
    """
    import sys; sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.email_parser  import parse_all_emails
    from pipeline.pdf_extractor import extract_from_bytes

    customers = dfs["customer"]
    products  = dfs["product"]
    pg        = dfs["product_group"][["group_code", "group_name"]]
    product_lines = dfs["product_line"][["line_id", "line_name"]]

    tax_to_cust = {str(r.tax_code): r.customer_code
                   for _, r in customers.iterrows() if r.tax_code}

    cust_idx  = customers.set_index("customer_code")
    prod_idx  = products.set_index("product_code")

    existing_so = set(dfs["sales_order"]["so_number"])

    emails = parse_all_emails(email_dir)
    logger.info(f"   T3 loader: {len(emails)} emails")

    rows = []
    ok = err = 0
    for ed in emails:
        if ed.error or not ed.attachment_bytes:
            err += 1; continue

        doc = extract_from_bytes(ed.attachment_bytes)
        if not doc.lines:
            err += 1; continue

        so    = doc.so_chung_tu or ed.so_number_body
        ngay  = doc.ngay_dat   or ed.order_date_body
        mst   = doc.mst        or ed.mst_body

        if not so or not ngay:
            err += 1; continue
        if so in existing_so:
            continue  # đã có trong SQL data

        try:
            d = datetime.strptime(ngay.strip(), "%d/%m/%Y")
            if not (d.year == 2026 and d.month == 3):
                err += 1; continue
            order_date = d.strftime("%Y-%m-%d")
        except ValueError:
            err += 1; continue

        cust_code = tax_to_cust.get(str(mst), "")
        cust_name = prov = region = ""
        if cust_code and cust_code in cust_idx.index:
            cr = cust_idx.loc[cust_code]
            cust_name = cr.get("customer_name", "")
            prov      = cr.get("province_name", "")
            region    = cr.get("region", "")

        for line in doc.lines:
            if line.so_luong <= 0:
                continue
            pc = str(line.ma_hang)
            prod_name = color = line_name = group_code = ""
            line_id = None
            if pc in prod_idx.index:
                pr        = prod_idx.loc[pc]
                prod_name = pr.get("product_name", "")
                color     = pr.get("color", "")
                line_id   = pr.get("line_id", None)
                line_name = pr.get("line_name", "")
                group_code= pr.get("group_code", "")

            rows.append({
                "order_id":       None,
                "so_number":      so,
                "product_code":   pc,
                "quantity":       float(line.so_luong),
                "unit_price":     float(line.don_gia),
                "line_total":     float(line.thanh_tien),
                "order_date":     order_date,
                "fiscal_year":    2026,
                "fiscal_month":   3,
                "fiscal_quarter": 1,
                "customer_code":  cust_code,
                "customer_name":  cust_name,
                "province_name":  prov,
                "region":         region,
                "product_name":   prod_name,
                "color":          color,
                "line_id":        line_id,
                "line_name":      line_name,
                "group_code":     group_code,
            })
        ok += 1

    t3 = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not t3.empty:
        t3 = t3.merge(pg, on="group_code", how="left")
        t3["order_date"] = pd.to_datetime(t3["order_date"])
        t3["product_code"] = t3["product_code"].astype(str)

    logger.info(f"   T3: {ok} orders OK | {err} lỗi | {len(t3)} order lines | "
                f"revenue={t3['line_total'].sum():,.0f}" if not t3.empty else
                f"   T3: {ok} orders OK | {err} lỗi | 0 lines")
    return t3
