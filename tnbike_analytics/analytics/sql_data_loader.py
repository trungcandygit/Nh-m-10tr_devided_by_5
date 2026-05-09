"""
Đọc dữ liệu từ file SQL sang pandas DataFrames — không cần PostgreSQL
Hỗ trợ toàn bộ schema tnbike: product_group, product_line, product,
province, customer, sales_order, order_line → fact_sales
"""
import re
import pandas as pd
from pathlib import Path


SQL_FILE = Path(__file__).parent.parent / "sql" / "02_import_data.sql"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_sql(path=None):
    p = Path(path) if path else SQL_FILE
    return p.read_text(encoding="utf-8")


def _extract_block(sql: str, table_name: str) -> str:
    """Lấy toàn bộ VALUES block của một INSERT INTO."""
    pattern = rf'INSERT INTO {re.escape(table_name)}\s*\([^)]+\)\s*VALUES\s*([\s\S]+?);'
    m = re.search(pattern, sql, re.IGNORECASE)
    return m.group(1) if m else ""


def _parse_rows_simple(block: str) -> list[tuple]:
    """
    Parse VALUES block không có subquery.
    Trả về list of tuples (raw strings).
    """
    rows = []
    # Bóc từng row: ('...', '...', NULL, 1.0, ...)
    row_re = re.compile(r'\(\s*((?:[^()\']*|\'(?:[^\'\\]|\\.)*\')*)\s*\)', re.DOTALL)
    for m in row_re.finditer(block):
        raw = m.group(1)
        cols = _split_csv(raw)
        rows.append(tuple(cols))
    return rows


def _split_csv(s: str) -> list:
    """Tách CSV có xét string literals."""
    parts, buf, in_str, esc = [], [], False, False
    for ch in s:
        if esc:
            buf.append(ch); esc = False
        elif ch == '\\' and in_str:
            buf.append(ch); esc = True
        elif ch == "'" and not in_str:
            in_str = True; buf.append(ch)
        elif ch == "'" and in_str:
            in_str = False; buf.append(ch)
        elif ch == ',' and not in_str:
            parts.append("".join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [_coerce(p) for p in parts]


def _coerce(s: str):
    """'value' → value, NULL → None, số → float/int."""
    s = s.strip()
    if s.upper() == 'NULL':
        return None
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    try:
        v = float(s)
        return int(v) if v == int(v) else v
    except (ValueError, OverflowError):
        return s


# ─────────────────────────────────────────────────────────────────────────────
# Table parsers
# ─────────────────────────────────────────────────────────────────────────────

def parse_product_groups(sql: str) -> pd.DataFrame:
    block = _extract_block(sql, "product_group")
    rows = _parse_rows_simple(block)
    df = pd.DataFrame(rows, columns=["group_code", "group_name", "description"])
    return df[["group_code", "group_name"]]


def parse_product_lines(sql: str) -> pd.DataFrame:
    block = _extract_block(sql, "product_line")
    rows = _parse_rows_simple(block)
    df = pd.DataFrame(rows, columns=["line_name", "group_code"])
    df.index = range(1, len(df) + 1)
    df["line_id"] = df.index
    return df


def parse_provinces(sql: str) -> pd.DataFrame:
    block = _extract_block(sql, "province")
    # Province names có thể chứa dấu xuống hàng trong string → strip
    rows = _parse_rows_simple(block)
    rows = [(r[0].replace("\n", "").replace("  ", " ").strip() if r[0] else r[0], r[1])
            for r in rows if len(r) >= 2]
    df = pd.DataFrame(rows, columns=["province_name", "region"])
    df.index = range(1, len(df) + 1)
    df["province_id"] = df.index
    return df


def parse_products(sql: str, product_lines: pd.DataFrame) -> pd.DataFrame:
    """Parse product — thay subquery line_id bằng giá trị thực."""
    block = _extract_block(sql, "product")

    # Lookup: (line_name, group_code) → line_id
    line_lookup = {(r.line_name, r.group_code): r.line_id
                   for _, r in product_lines.iterrows()}

    # Pattern cho từng row: ('code', 'name', (SELECT ... WHERE line_name = 'X' AND group_code = 'Y' ...), 'color', 'unit')
    row_re = re.compile(
        r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*"   # code, name
        r"((?:\(SELECT[^)]+\))|NULL)\s*,\s*"         # line_id subquery or NULL
        r"'([^']*)'\s*,\s*'([^']*)'\s*\)",           # color, unit
        re.IGNORECASE
    )

    rows = []
    for m in row_re.finditer(block):
        code, name, line_sub, color, unit = m.groups()
        line_id = None
        if "SELECT" in line_sub.upper():
            # Trích line_name và group_code từ subquery
            mn = re.search(r"line_name\s*=\s*'([^']+)'", line_sub)
            mg = re.search(r"group_code\s*=\s*'([^']+)'", line_sub)
            if mn and mg:
                line_id = line_lookup.get((mn.group(1), mg.group(1)))
        rows.append((code, name, line_id, color.strip(), unit.strip()))

    df = pd.DataFrame(rows, columns=["product_code", "product_name", "line_id", "color", "unit"])
    # Join group via line_id
    line_sub = product_lines[["line_id", "line_name", "group_code"]].copy()
    df = df.merge(line_sub, on="line_id", how="left")
    return df


def parse_customers(sql: str, provinces: pd.DataFrame) -> pd.DataFrame:
    """Parse customer — thay subquery province_id."""
    block = _extract_block(sql, "customer")

    prov_lookup = {r.province_name: r.province_id for _, r in provinces.iterrows()}

    row_re = re.compile(
        r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*"     # customer_code, name
        r"'([^']*)'\s*,\s*"                             # tax_code
        r"(NULL|'[^']*')\s*,\s*"                        # address
        r"((?:\(SELECT[^)]+\))|NULL)\s*\)",             # province_id
        re.IGNORECASE | re.DOTALL
    )

    rows = []
    for m in row_re.finditer(block):
        code, name, tax, addr_raw, prov_sub = m.groups()
        addr = addr_raw[1:-1] if addr_raw != "NULL" else None
        prov_id = None
        if "SELECT" in prov_sub.upper():
            mp = re.search(r"province_name\s*=\s*'([^']+)'", prov_sub)
            if mp:
                prov_id = prov_lookup.get(mp.group(1))
        rows.append((code, name, tax, addr, prov_id))

    df = pd.DataFrame(rows, columns=["customer_code", "customer_name", "tax_code", "address", "province_id"])
    prov_sub = provinces[["province_id", "province_name", "region"]].copy()
    df = df.merge(prov_sub, on="province_id", how="left")
    return df


def parse_sales_orders(sql: str) -> pd.DataFrame:
    block = _extract_block(sql, "sales_order")
    rows = _parse_rows_simple(block)
    df = pd.DataFrame(rows, columns=["so_number", "invoice_symbol", "invoice_number", "order_date", "customer_code"])
    df["order_date"]    = pd.to_datetime(df["order_date"])
    df["fiscal_year"]   = df["order_date"].dt.year
    df["fiscal_month"]  = df["order_date"].dt.month
    df["fiscal_quarter"]= df["order_date"].dt.quarter
    df["order_id"]      = range(1, len(df) + 1)
    return df


def parse_order_lines(sql: str, orders: pd.DataFrame) -> pd.DataFrame:
    """Parse order_line — thay subquery order_id bằng so_number lookup."""
    block = _extract_block(sql, "order_line")

    so_lookup = {r.so_number: r.order_id for _, r in orders.iterrows()}

    row_re = re.compile(
        r"\(\s*(?:\(SELECT order_id FROM sales_order WHERE so_number = '([^']+)'[^)]*\)|NULL)\s*,"
        r"\s*'([^']+)'\s*,"      # so_number
        r"\s*'([^']+)'\s*,"      # product_code
        r"\s*([\d.]+)\s*,"       # quantity
        r"\s*([\d.]+)\s*,"       # unit_price
        r"\s*([\d.]+)\s*\)",     # line_total
        re.IGNORECASE
    )

    rows = []
    for m in row_re.finditer(block):
        so_in_sub, so_number, product_code, qty, price, total = m.groups()
        so = so_in_sub or so_number
        order_id = so_lookup.get(so)
        rows.append((order_id, so_number, product_code, float(qty), float(price), float(total)))

    df = pd.DataFrame(rows, columns=["order_id", "so_number", "product_code", "quantity", "unit_price", "line_total"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Main loader
# ─────────────────────────────────────────────────────────────────────────────

def load_all(sql_path=None) -> dict:
    """Trả về dict tất cả DataFrames."""
    sql = _read_sql(sql_path)
    dfs = {}
    dfs["product_group"] = parse_product_groups(sql)
    dfs["product_line"]  = parse_product_lines(sql)
    dfs["province"]      = parse_provinces(sql)
    dfs["product"]       = parse_products(sql, dfs["product_line"])
    dfs["customer"]      = parse_customers(sql, dfs["province"])
    dfs["sales_order"]   = parse_sales_orders(sql)
    dfs["order_line"]    = parse_order_lines(sql, dfs["sales_order"])
    return dfs


def build_fact(dfs: dict) -> pd.DataFrame:
    """Join tất cả bảng thành fact_sales phẳng."""
    ol  = dfs["order_line"]
    so  = dfs["sales_order"][["order_id", "so_number", "order_date", "fiscal_year",
                               "fiscal_month", "fiscal_quarter", "customer_code"]]
    cus = dfs["customer"][["customer_code", "customer_name", "province_name", "region"]]
    prod = dfs["product"][["product_code", "product_name", "color", "line_id",
                            "line_name", "group_code"]]
    pg  = dfs["product_group"][["group_code", "group_name"]]

    fact = (
        ol
        .merge(so,   on=["order_id", "so_number"], how="left")
        .merge(cus,  on="customer_code",           how="left")
        .merge(prod, on="product_code",            how="left")
        .merge(pg,   on="group_code",              how="left")
    )
    return fact
