"""
Ghi dữ liệu đã validate vào PostgreSQL — tnbike schema
Thứ tự ghi: email_log → sales_order → order_line → fact_sales (refresh)
"""
import logging
from datetime import datetime, date
from .db_connection import get_connection
from .validator import Status

logger = logging.getLogger("tnbike.db_writer")


def _parse_date_safe(s: str) -> date:
    from .validator import _parse_date
    try:
        return _parse_date(s).date()
    except Exception:
        return date(2026, 3, 15)


def write_full_order(email_data, order_doc, validation_result) -> dict:
    """
    Ghi 1 đơn hàng vào DB trong 1 transaction.
    Returns: {"order_id", "log_id", "status"}
    """
    with get_connection() as conn:
        cur = conn.cursor()

        # 1. email_log
        from psycopg2.extras import execute_values
        cur.execute("""
            INSERT INTO email_log
                (message_id, from_address, received_at, subject,
                 attachment_name, processing_status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (message_id) DO UPDATE SET
                processing_status = EXCLUDED.processing_status,
                error_message     = EXCLUDED.error_message,
                processed_at      = NOW()
            RETURNING log_id
        """, (
            email_data.message_id,
            email_data.from_address,
            email_data.received_at or None,
            email_data.subject,
            email_data.attachment_name,
            validation_result.status.value,
            "; ".join(validation_result.errors) if validation_result.errors else None,
        ))
        log_id = cur.fetchone()[0]

        if validation_result.status == Status.INVALID:
            return {"order_id": None, "log_id": log_id, "status": "INVALID"}

        # 2. sales_order
        order_date    = _parse_date_safe(order_doc.ngay_dat or email_data.order_date_body)
        customer_code = order_doc.ma_dai_ly or ""
        so_number     = order_doc.so_chung_tu

        if not customer_code:
            return {"order_id": None, "log_id": log_id, "status": "INVALID"}

        cur.execute("""
            INSERT INTO sales_order (so_number, invoice_symbol, order_date, customer_code)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (so_number) DO NOTHING
            RETURNING order_id
        """, (so_number, "C26TTN", order_date, customer_code))
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT order_id FROM sales_order WHERE so_number = %s", (so_number,))
            row = cur.fetchone()
        order_id = row[0]

        # 3. order_line (batch insert)
        line_data = [
            (order_id, so_number, line.ma_hang, line.so_luong, line.don_gia, line.thanh_tien)
            for line in order_doc.lines
            if line.ma_hang and line.so_luong > 0
        ]
        if line_data:
            execute_values(cur, """
                INSERT INTO order_line (order_id, so_number, product_code, quantity, unit_price, line_total)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, line_data)

        # 4. cập nhật email_log
        cur.execute("UPDATE email_log SET order_id = %s WHERE log_id = %s", (order_id, log_id))

    return {"order_id": order_id, "log_id": log_id, "status": "OK"}


def refresh_fact_sales(year: int = 2026, month: int = 3):
    """UPSERT fact_sales cho T3/2026 sau khi ghi xong toàn bộ đơn hàng."""
    sql = f"""
    INSERT INTO fact_sales (
        order_date, fiscal_year, fiscal_quarter, fiscal_month, week_of_year,
        so_number, order_id, line_id,
        customer_code, customer_name, province_id, province_name, region,
        product_code, product_name, color, line_id_fk, line_name, group_code, group_name,
        quantity, unit_price, line_total
    )
    SELECT
        so.order_date,
        so.fiscal_year, so.fiscal_quarter, so.fiscal_month,
        EXTRACT(WEEK FROM so.order_date)::SMALLINT,
        ol.so_number, ol.order_id, ol.line_id,
        c.customer_code, c.customer_name, c.province_id, p.province_name, p.region,
        pr.product_code, pr.product_name, pr.color,
        pr.line_id, pl.line_name, pg.group_code, pg.group_name,
        ol.quantity, ol.unit_price, ol.line_total
    FROM order_line ol
    JOIN sales_order   so ON so.order_id      = ol.order_id
    JOIN customer       c ON c.customer_code  = so.customer_code
    LEFT JOIN province  p ON p.province_id    = c.province_id
    JOIN product       pr ON pr.product_code  = ol.product_code
    LEFT JOIN product_line  pl ON pl.line_id  = pr.line_id
    LEFT JOIN product_group pg ON pg.group_code = pl.group_code
    WHERE so.fiscal_year = {year} AND so.fiscal_month = {month}
    ON CONFLICT DO NOTHING
    """
    with get_connection() as conn:
        conn.cursor().execute(sql)
    logger.info(f"Đã refresh fact_sales {month}/{year}")
