"""
Kết nối PostgreSQL — Xe đạp Thống Nhất tnbike_db
"""
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA

logger = logging.getLogger("tnbike.db")


@contextmanager
def get_connection():
    """Context manager kết nối PostgreSQL — tự commit hoặc rollback."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            options=f"-c search_path={DB_SCHEMA},public"
        )
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Lỗi DB, đã rollback: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_engine():
    """SQLAlchemy engine cho pandas.read_sql()"""
    from sqlalchemy import create_engine
    from config import DB_URL
    return create_engine(
        DB_URL,
        connect_args={"options": f"-c search_path={DB_SCHEMA},public"}
    )


def load_reference_data(conn) -> dict:
    """Cache mã hàng, mã đại lý hợp lệ và đơn hàng đã có trong T3/2026."""
    cur = conn.cursor()

    cur.execute("SELECT product_code FROM product WHERE is_active = TRUE")
    valid_products = {r[0] for r in cur.fetchall()}

    cur.execute("SELECT customer_code, tax_code FROM customer WHERE is_active = TRUE")
    rows = cur.fetchall()
    valid_customers = {r[0] for r in rows}
    tax_to_customer = {r[1]: r[0] for r in rows if r[1]}

    cur.execute("SELECT so_number FROM sales_order WHERE fiscal_year = 2026 AND fiscal_month = 3")
    existing_orders = {r[0] for r in cur.fetchall()}

    logger.info(
        f"Đã load: {len(valid_products)} SKU | "
        f"{len(valid_customers)} đại lý | "
        f"{len(existing_orders)} đơn T3/2026 đã có"
    )
    return {
        "valid_products":  valid_products,
        "valid_customers": valid_customers,
        "tax_to_customer": tax_to_customer,
        "existing_orders": existing_orders,
    }
