-- Dimension bảng ngày cho phân tích thời gian & mùa vụ Việt Nam
SET search_path TO tnbike, public;

CREATE TABLE IF NOT EXISTS dim_date (
    date_key        DATE        PRIMARY KEY,
    year            SMALLINT,
    quarter         SMALLINT,
    month           SMALLINT,
    week_of_year    SMALLINT,
    day_of_week     SMALLINT,   -- 1=Thứ Hai … 7=Chủ Nhật (ISO)
    day_name_vn     VARCHAR(15),
    month_name_vn   VARCHAR(20),
    is_weekend      BOOLEAN,
    is_tet          BOOLEAN DEFAULT FALSE,
    is_holiday_vn   BOOLEAN DEFAULT FALSE,
    season_vn       VARCHAR(10),
    school_season   VARCHAR(20)
);

INSERT INTO dim_date
SELECT
    d::date,
    EXTRACT(YEAR    FROM d)::SMALLINT,
    EXTRACT(QUARTER FROM d)::SMALLINT,
    EXTRACT(MONTH   FROM d)::SMALLINT,
    EXTRACT(WEEK    FROM d)::SMALLINT,
    EXTRACT(ISODOW  FROM d)::SMALLINT,
    CASE EXTRACT(ISODOW FROM d)
        WHEN 1 THEN 'Thứ Hai'  WHEN 2 THEN 'Thứ Ba'
        WHEN 3 THEN 'Thứ Tư'   WHEN 4 THEN 'Thứ Năm'
        WHEN 5 THEN 'Thứ Sáu'  WHEN 6 THEN 'Thứ Bảy'
        WHEN 7 THEN 'Chủ Nhật'
    END,
    'Tháng ' || EXTRACT(MONTH FROM d)::TEXT,
    EXTRACT(ISODOW FROM d) IN (6,7),
    FALSE,
    FALSE,
    CASE
        WHEN EXTRACT(MONTH FROM d) IN (1,2,3)  THEN 'Xuân'
        WHEN EXTRACT(MONTH FROM d) IN (4,5,6)  THEN 'Hạ'
        WHEN EXTRACT(MONTH FROM d) IN (7,8,9)  THEN 'Thu'
        ELSE 'Đông'
    END,
    CASE
        WHEN EXTRACT(MONTH FROM d) IN (8,9)    THEN 'Tựu trường'
        WHEN EXTRACT(MONTH FROM d) IN (6,7)    THEN 'Nghỉ hè'
        ELSE 'Bình thường'
    END
FROM generate_series('2025-01-01'::date, '2026-12-31'::date, '1 day') d
ON CONFLICT (date_key) DO NOTHING;

-- Đánh dấu Tết Nguyên Đán
UPDATE dim_date SET is_tet = TRUE
WHERE (date_key BETWEEN '2025-01-29' AND '2025-02-05')
   OR (date_key BETWEEN '2026-02-17' AND '2026-02-24');

-- Đánh dấu ngày lễ Việt Nam
UPDATE dim_date SET is_holiday_vn = TRUE
WHERE (EXTRACT(MONTH FROM date_key) = 4  AND EXTRACT(DAY FROM date_key) = 30)
   OR (EXTRACT(MONTH FROM date_key) = 5  AND EXTRACT(DAY FROM date_key) = 1)
   OR (EXTRACT(MONTH FROM date_key) = 9  AND EXTRACT(DAY FROM date_key) = 2)
   OR (EXTRACT(MONTH FROM date_key) = 1  AND EXTRACT(DAY FROM date_key) = 1);
