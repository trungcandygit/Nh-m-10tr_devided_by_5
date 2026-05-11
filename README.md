# tnbike_analytics — DATA EXPLORERS 2026 Vòng 2

Hệ thống phân tích dữ liệu kinh doanh **Công ty Xe đạp Thống Nhất**
Phạm vi: Q1-2025 + Q1-2026 | 702 đại lý | 247 SKU | 5 nhóm sản phẩm

---

## Cấu trúc dự án

```
tnbike_analytics/
│
├── export_master.py             # ENTRY POINT — SQL → 2 CSV dashboard
│
├── analytics/
│   └── sql_data_loader.py       # Parse sql/02_import_data.sql → DataFrames
│                                # (không cần PostgreSQL)
│
├── pipeline/                    # Hạng mục A — Xử lý email + PDF T3/2026
│   ├── email_parser.py          # Parse .eml, trích metadata + PDF attachment
│   ├── pdf_extractor.py         # Bóc nội dung PDF đặt hàng (pdftotext)
│   ├── validator.py             # Kiểm tra hợp lệ trước khi ghi DB
│   ├── db_connection.py         # PostgreSQL context manager
│   ├── db_writer.py             # Ghi email_log → sales_order → order_line
│   └── run_pipeline.py          # Entry point: xử lý 1.132 email T3/2026
│
├── sql/
│   ├── 01_create_tables.sql     # Schema: 9 bảng + 4 views + triggers
│   ├── 02_import_data.sql       # Data Q1-2025 + Q1-2026 (17.031 dòng)
│   ├── 03_email_log.sql         # Bảng log pipeline A
│   ├── 04_dim_date.sql          # Dimension ngày (mùa vụ VN)
│   └── 05_views_extra.sql       # Views tổng hợp
│
├── tests/
│   ├── test_analytics.py        # 21 tests — analytics core (không cần DB)
│   ├── test_email_parser.py
│   ├── test_pdf_extractor.py
│   └── test_validator.py
│
├── data/
│   ├── raw/emails/              # Đặt file .eml vào đây (gitignored)
│   └── raw/pdfs/                # Đặt file .pdf vào đây (gitignored)
│
└── output/
    └── master/                  # OUTPUT — 2 CSV dùng cho dashboard
        ├── fact_full.csv        # 17.031 rows × 48 cols (6 MB)
        └── agg_master.csv       #  2.097 rows × 70 cols (449 KB)
```

---

## Output CSV

### `output/master/fact_full.csv` — 17.031 rows × 48 cols
Mỗi row = 1 dòng order line + toàn bộ enrichment join về:

| Nhóm cột | Nội dung |
|---|---|
| Giao dịch | order_id, so_number, product_code, quantity, unit_price, line_total |
| Thời gian | order_date, fiscal_year/month/quarter, ym, period_label, day_of_week |
| Đơn hàng | order_total, n_lines_in_order, line_share_of_order_pct |
| Địa lý | customer_code/name, province_name, region |
| Sản phẩm | product_name, color, line_name, group_code/name |
| SKU metrics | sku_revenue_rank, sku_pareto_class, sku_bcg_quadrant, sku_yoy_rev_pct |
| Khách hàng | cust_cohort_month, cust_rfm_r/f/m, cust_rfm_segment |
| Churn ML | cust_churn_label, cust_churn_prob, cust_churn_priority |

### `output/master/agg_master.csv` — 2.097 rows × 70 cols
Tất cả aggregations trong 1 file — dùng cột `grain` để lọc:

| `grain` | Mô tả | Dùng để vẽ |
|---|---|---|
| `monthly_group_region` | Tháng × nhóm SP × vùng | Line chart, area trend |
| `monthly_group` | Tháng × nhóm SP (tổng) | Bar trend, MoM/YoY |
| `monthly_region` | Tháng × vùng | Regional trend |
| `monthly_total` | Tổng quốc gia theo tháng | KPI trend |
| `province_group` | Tỉnh × nhóm SP | Heatmap |
| `province_total` | Tổng theo tỉnh | Map, bar chart tỉnh |
| `region_group` | Vùng × nhóm SP | Stacked bar |
| `region_total` | Tổng theo vùng | Pie/donut |
| `national_group` | Quốc gia × nhóm SP | Summary bar |
| `national_total` | Tổng toàn quốc | Single KPI |
| `sku` | Từng SKU (161 sản phẩm) | BCG bubble, Pareto, top SKU |
| `customer` | Từng khách hàng (333) | Churn table, RFM scatter |
| `forecast_daily` | Dự báo daily × nhóm SP | Forecast band chart |

```python
# Ví dụ dùng trong Dash
# QUAN TRỌNG: product_code phải đọc là string để giữ leading zeros
STR_COLS = {"product_code": str}
df   = pd.read_csv("output/master/agg_master.csv",  dtype=STR_COLS)
fact = pd.read_csv("output/master/fact_full.csv",   dtype=STR_COLS)

monthly  = df[df.grain == "monthly_group_region"]
province = df[df.grain == "province_total"]
sku      = df[df.grain == "sku"]
customer = df[df.grain == "customer"]
forecast = df[df.grain == "forecast_daily"]
```

---

## Cài đặt & Chạy

```bash
pip install -r requirements.txt

# Tạo 2 CSV dashboard
python tnbike_analytics/export_master.py

# Chạy tests
cd tnbike_analytics && pytest tests/
```

**Output mẫu:**
```
INFO  0. Loading fact table from SQL...
INFO     17,031 rows | 2025-01-02 → 2026-02-28
INFO  1. Computing SKU enrichment...
INFO  2. Computing customer RFM + Churn ML...
INFO     ROC-AUC (held-out test): 0.841
INFO  3. Running Prophet forecast...
INFO  4. Building fact_full.csv...   → 17,031 rows × 48 cols
INFO  5. Building agg_master.csv...  →  2,097 rows × 70 cols
```

---

## Pipeline A — Xử lý email T3/2026

Yêu cầu: PostgreSQL + file .eml/.pdf trong `data/raw/`

```bash
# Cấu hình DB
cp .env.example .env  # sửa thông tin PostgreSQL

# Khởi tạo schema
psql -U postgres -d tnbike_db -f sql/01_create_tables.sql
psql -U postgres -d tnbike_db -f sql/02_import_data.sql
psql -U postgres -d tnbike_db -f sql/03_email_log.sql

# Chạy pipeline
python -m pipeline.run_pipeline \
  --email-dir data/raw/emails \
  --pdf-dir   data/raw/pdfs
```

---

## ML / Forecast

### Churn Prediction (customer grain)
- **Feature period:** Q1-2025 (Jan–Mar 2025)
- **Label:** khách hàng không mua lại trong Q1-2026 → churn = 1
- **Model:** `Pipeline(StandardScaler + LogisticRegression)` — không data leakage
- **Split:** 80/20 StratifiedShuffleSplit
- **ROC-AUC held-out test: 0.841**

### Demand Forecast (forecast_daily grain)
- **Train:** 2025-01 → 2026-01
- **Test (backtest):** 2026-02 (so sánh với thực tế)
- **Forecast:** 2026-03 → 2026-06
- **Model:** Prophet (logistic growth + VN holidays, yearly_seasonality=False)

---

## Schema

| Bảng | Mô tả |
|---|---|
| `product_group` | 5 nhóm sản phẩm |
| `product_line` | 72 dòng xe |
| `product` | 247 SKU |
| `province` | 63 tỉnh thành |
| `customer` | 702 đại lý |
| `sales_order` | Đầu phiếu bán hàng |
| `order_line` | Dòng hàng hóa |
| `email_log` | Log pipeline A |

**5 nhóm sản phẩm:**

| Code | Tên |
|---|---|
| `CITYBIKE_P` | Xe phổ thông |
| `KIDBIKE_1` | Xe trẻ em nhóm 1 |
| `KIDBIKE_2` | Xe trẻ em nhóm 2 |
| `SPORTBIKE_S` | Xe thể thao khung thép |
| `SPORTBIKE_A` | Xe thể thao khung nhôm |

---

## Stack

| Layer | Công nghệ |
|---|---|
| Data source | SQL file (không cần DB để analytics) |
| Analytics / ML | pandas, scikit-learn, prophet |
| Dashboard | Dash / Plotly (dùng output/master/*.csv) |
| Pipeline A | psycopg2, pdftotext (poppler) |
| Tests | pytest (36 tests total) |
