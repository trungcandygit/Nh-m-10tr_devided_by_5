-- Views bổ sung cho analytics
SET search_path TO tnbike, public;

-- View: Pipeline summary
CREATE OR REPLACE VIEW v_pipeline_summary AS
SELECT
    processing_status,
    COUNT(*)                    AS so_email,
    COUNT(order_id)             AS so_don_tao_duoc,
    MIN(received_at)            AS earliest,
    MAX(received_at)            AS latest,
    MAX(processed_at)           AS last_processed
FROM email_log
GROUP BY processing_status;

COMMENT ON VIEW v_pipeline_summary IS 'Tổng kết kết quả chạy pipeline A';

-- View: Churn candidates
CREATE OR REPLACE VIEW v_churn_candidates AS
SELECT
    c.customer_code,
    c.customer_name,
    p.province_name,
    p.region,
    COUNT(DISTINCT so.so_number)            AS total_orders,
    SUM(ol.line_total)                      AS total_revenue,
    MAX(so.order_date)                      AS last_order_date,
    CURRENT_DATE - MAX(so.order_date)       AS days_since_last_order,
    CASE
        WHEN CURRENT_DATE - MAX(so.order_date) >= 180 THEN 'Đã mất'
        WHEN CURRENT_DATE - MAX(so.order_date) >= 90  THEN 'Nguy cơ rời bỏ'
        WHEN CURRENT_DATE - MAX(so.order_date) >= 60  THEN 'Cần chú ý'
        ELSE 'Hoạt động'
    END                                     AS churn_status
FROM customer c
LEFT JOIN sales_order so ON so.customer_code = c.customer_code
LEFT JOIN order_line   ol ON ol.order_id = so.order_id
LEFT JOIN province      p ON p.province_id = c.province_id
WHERE c.is_active = TRUE
GROUP BY c.customer_code, c.customer_name, p.province_name, p.region
ORDER BY days_since_last_order DESC NULLS LAST;

COMMENT ON VIEW v_churn_candidates IS 'Đại lý có nguy cơ rời bỏ — dùng cho alert hệ thống';
