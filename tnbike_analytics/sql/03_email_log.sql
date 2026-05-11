-- Bảng ghi log xử lý email — Hạng mục A
-- Chạy sau 01_create_tables.sql
SET search_path TO tnbike, public;

CREATE TABLE IF NOT EXISTS email_log (
    log_id              SERIAL          PRIMARY KEY,
    message_id          VARCHAR(200)    UNIQUE,
    from_address        VARCHAR(200),
    received_at         TIMESTAMPTZ,
    subject             VARCHAR(300),
    attachment_name     VARCHAR(200),
    processing_status   VARCHAR(20)     DEFAULT 'PENDING',
    -- PENDING | VALID | INVALID | WARNING | SKIPPED
    error_message       TEXT,
    order_id            INTEGER         REFERENCES sales_order(order_id),
    processed_at        TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_log_status   ON email_log(processing_status);
CREATE INDEX IF NOT EXISTS idx_email_log_received ON email_log(received_at);
CREATE INDEX IF NOT EXISTS idx_email_log_order    ON email_log(order_id);

COMMENT ON TABLE  email_log IS 'Log xử lý 1.132 email đặt hàng T3/2026 — Hạng mục A';
COMMENT ON COLUMN email_log.processing_status IS 'PENDING/VALID/INVALID/WARNING/SKIPPED';
