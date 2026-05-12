# tnbike_analytics — DATA EXPLORERS 2026 Vòng 2

Hệ thống phân tích dữ liệu kinh doanh **Công ty Xe đạp Thống Nhất**
Phạm vi: Q1-2025 + Q1-2026 + T3/2026 (email pipeline) | 703 đại lý | 265 SKU | 5 nhóm sản phẩm

---

## Cấu trúc dự án

```
Nh-m-10tr_devided_by_5/               # Repo root
│
├── .gitignore                         # Loại trừ de_thi/emails/ và de_thi/pdfs/
├── README.md
│
├── de_thi/                            # Đề thi + dữ liệu gốc
│   ├── emails/                        # 1.132 file .eml (gitignored)
│   ├── pdfs/                          # 1.132 file .pdf (gitignored)
│   ├── tnbike_emails_mar2026.rar
│   ├── tnbike_pdfs_mar2026.rar
│   ├── 01_create_tables.sql
│   ├── 02_import_data.sql
│   └── DataExplorers2026 - Đề thi Vòng 2 (2).pdf
│
└── tnbike_analytics/
    │
    ├── export_master.py               # Pipeline cũ — SQL → master/*.csv
    ├── export_csv.py                  # ENTRY POINT MỚI → output/data/ + output/prediction/
    │
    ├── analytics/
    │   ├── sql_data_loader.py         # Parse sql/02_import_data.sql → DataFrames
    │   └── t3_loader.py               # Parse 1.132 email+PDF T3/2026 → DataFrame
    │                                  # (pdftotext, không cần PostgreSQL)
    │
    ├── pipeline/                      # Hạng mục A — Xử lý email + PDF T3/2026
    │   ├── email_parser.py
    │   ├── pdf_extractor.py
    │   ├── validator.py
    │   ├── db_connection.py
    │   ├── db_writer.py
    │   └── run_pipeline.py
    │
    ├── dashboard/                     # Dash app 6 trang (port 8050)
    │   ├── index.py                   # Entry point + routing
    │   ├── app.py
    │   ├── data_loader.py             # Load output/data/ + output/prediction/
    │   ├── assets/style.css
    │   ├── requirements.txt
    │   └── pages/
    │       ├── p1_overview.py         # KPI + xu hướng doanh thu
    │       ├── p2_product.py          # Pareto, BCG, màu sắc
    │       ├── p3_dealer.py           # RFM + Churn
    │       ├── p4_geo.py              # Tỉnh thành, vùng
    │       ├── p5_forecast.py         # Prophet Q2 + dealer activity
    │       └── p6_ops.py              # Vận hành pipeline email
    │
    ├── sql/
    │   ├── 01_create_tables.sql
    │   ├── 02_import_data.sql
    │   ├── 03_email_log.sql
    │   ├── 04_dim_date.sql
    │   └── 05_views_extra.sql
    │
    ├── tests/
    │   ├── test_analytics.py          # 21 tests — analytics core
    │   ├── test_email_parser.py
    │   ├── test_pdf_extractor.py
    │   └── test_validator.py
    │
    ├── data/
    │   ├── raw/emails/ → ../../de_thi/emails/   # symlink (gitignored)
    │   └── raw/pdfs/   → ../../de_thi/pdfs/     # symlink (gitignored)
    │
    └── output/
        ├── data/                      # Dữ liệu thực tế (không có dự báo / ML output)
        │   ├── raw_history.csv        # 17,031 rows — Q1-2025 + Q1-Feb2026 từ SQL
        │   ├── raw_t3_orders.csv      #  8,559 rows — T3/2026 từ email pipeline
        │   ├── kpi_overview.csv       #     12 rows — 12 KPI tổng hợp
        │   ├── monthly_trend.csv      #     36 rows — tháng × nhóm: DT, SL, YoY, MoM
        │   ├── product_analysis.csv   #    161 rows — SKU: Pareto A/B/C, BCG, YoY
        │   ├── color_analysis.csv     #    328 rows — màu × nhóm × tháng
        │   ├── color_history.csv      #    329 rows — tỷ trọng màu theo tháng
        │   ├── dealer_rfm.csv         #    333 rows — đại lý: RFM features & segments
        │   ├── geo_province.csv       #     74 rows — tỉnh: DT, rank, share
        │   ├── geo_region.csv         #     20 rows — vùng × nhóm SP
        │   ├── ops_pipeline.csv       #      8 rows — thống kê pipeline email T3
        │   └── ops_daily.csv          #     31 rows — DT + đơn mỗi ngày T3/2026
        │
        └── prediction/                # Dữ liệu dự báo & ML output
            ├── dealer_churn.csv       #    333 rows — LogReg: P(churn), nhãn, train/test
            ├── dealer_activity.csv    #    703 rows — P(đặt hàng 30 ngày tới)
            ├── revenue_q2_daily.csv   #  1,041 rows — Prophet: dự báo daily Q2/2026
            ├── revenue_q2_monthly.csv #     49 rows — Prophet: dự báo monthly Q2/2026
            └── color_q2.csv          #    183 rows — dự báo tỷ trọng màu Q2/2026
```

---

## Output CSV

### `output/data/` — Dữ liệu thực tế (12 file)

| File | Rows | Mô tả |
|---|---|---|
| `raw_history.csv` | 17,031 | Order line thô — Q1-2025 + Q1-Feb2026 từ SQL |
| `raw_t3_orders.csv` | 8,559 | Order line thô — T3/2026 từ email pipeline |
| `kpi_overview.csv` | 12 | KPI: doanh thu, đơn hàng, đại lý, T3 stats |
| `monthly_trend.csv` | 36 | Tháng × nhóm SP: DT, SL, YoY, MoM, YTD |
| `product_analysis.csv` | 161 | SKU: Pareto A/B/C, BCG (Ngôi sao/Bò sữa/Dấu hỏi/Con chó), YoY |
| `color_analysis.csv` | 328 | Màu × nhóm × tháng: DT, SL |
| `color_history.csv` | 329 | Tỷ trọng (%) màu sắc theo tháng |
| `dealer_rfm.csv` | 333 | Đại lý: recency, frequency, monetary, RFM segment |
| `geo_province.csv` | 74 | Tỉnh: DT, rank quốc gia + vùng, share % |
| `geo_region.csv` | 20 | Vùng × nhóm SP |
| `ops_pipeline.csv` | 8 | Pipeline T3: tổng email, OK, lỗi, tỷ lệ |
| `ops_daily.csv` | 31 | Đơn hàng + doanh thu từng ngày T3/2026 |

### `output/prediction/` — Dự báo & ML output (5 file)

| File | Rows | Mô tả |
|---|---|---|
| `dealer_churn.csv` | 333 | LogReg: P(churn), churn_priority, train/test split, ROC-AUC |
| `dealer_activity.csv` | 703 | P(đặt hàng trong 30 ngày tới), activity_risk, priority_contact |
| `revenue_q2_daily.csv` | 1,041 | Prophet: yhat/lower/upper theo ngày × nhóm SP (Q2/2026) |
| `revenue_q2_monthly.csv` | 49 | Prophet: tổng hợp theo tháng × nhóm SP |
| `color_q2.csv` | 183 | Dự báo DT theo màu × nhóm × tháng Q2 (share-based) |

```python
# Đọc CSV — QUAN TRỌNG: product_code phải là string để giữ leading zeros
STR_COLS = {"product_code": str}

# Dữ liệu thực tế
kpi     = pd.read_csv("output/data/kpi_overview.csv")
monthly = pd.read_csv("output/data/monthly_trend.csv")
sku     = pd.read_csv("output/data/product_analysis.csv", dtype=STR_COLS)
dealer  = pd.read_csv("output/data/dealer_rfm.csv")

# Dự báo & ML
churn    = pd.read_csv("output/prediction/dealer_churn.csv")
fcst     = pd.read_csv("output/prediction/revenue_q2_monthly.csv")
activity = pd.read_csv("output/prediction/dealer_activity.csv")

# Join churn vào dealer khi cần cả RFM + churn
dealer_full = dealer.merge(churn, on="customer_code", how="left")
```

---

## Cài đặt & Chạy

```bash
pip install -r requirements.txt

# Giải nén dữ liệu email/PDF (nếu chưa có)
cd de_thi
unrar e tnbike_emails_mar2026.rar emails/
unrar e tnbike_pdfs_mar2026.rar   pdfs/

# Sinh toàn bộ CSV (data/ + prediction/)
cd tnbike_analytics
python export_csv.py

# Chạy dashboard (6 trang)
cd dashboard && python index.py
# → http://localhost:8050

# Chạy tests
pytest tests/
```

**Output mẫu `export_csv.py`:**
```
INFO  Loading data...
INFO     T3: 1112 orders OK | 20 lỗi | 8559 order lines | revenue=39,909,335,753
INFO  === DATA/ ===
INFO    raw_history.csv           17,031 rows
INFO    raw_t3_orders.csv          8,559 rows  (1112 orders)
INFO    kpi_overview.csv             12 rows
INFO    monthly_trend.csv            36 rows
INFO    product_analysis.csv        161 rows
INFO    color_analysis.csv          328 rows
INFO    color_history.csv           329 rows
INFO    dealer_rfm.csv              333 rows
INFO    geo_province.csv             74 rows
INFO    geo_region.csv               20 rows
INFO    ops_pipeline.csv               8 rows
INFO    ops_daily.csv                 31 rows
INFO  === PREDICTION/ ===
INFO     Churn model ROC-AUC test: 0.775
INFO    dealer_churn.csv            333 rows
INFO     Prophet: 6 groups
INFO    revenue_q2_daily.csv      1,041 rows
INFO    revenue_q2_monthly.csv       49 rows
INFO    color_q2.csv                183 rows
INFO    dealer_activity.csv         703 rows
```

---

## Pipeline A — Xử lý email T3/2026

Yêu cầu: PostgreSQL + file .eml/.pdf trong `data/raw/`

```bash
cp .env.example .env   # sửa thông tin PostgreSQL
psql -U postgres -d tnbike_db -f sql/01_create_tables.sql
psql -U postgres -d tnbike_db -f sql/02_import_data.sql
psql -U postgres -d tnbike_db -f sql/03_email_log.sql

python -m pipeline.run_pipeline \
  --email-dir data/raw/emails \
  --pdf-dir   data/raw/pdfs
```

---

## ML / Forecast

### Churn Prediction → `prediction/dealer_churn.csv`
- **Feature period:** Q1-2025 (Jan–Mar 2025)
- **Label:** khách hàng không mua lại trong Q1-2026 → churn = 1
- **Model:** `Pipeline(StandardScaler + LogisticRegression(C=1.0))` — không data leakage
- **Split:** 80/20 StratifiedShuffleSplit
- **ROC-AUC held-out test: 0.775**

### Dealer Activity → `prediction/dealer_activity.csv`
- **Model:** cùng LogReg pipeline, áp dụng cho toàn bộ 703 đại lý
- **Output:** `prob_active_30d`, `activity_risk`, `priority_contact`

### Demand Forecast → `prediction/revenue_q2_*.csv`
- **Train:** Jan 2025 → Mar 2026 (daily, per nhóm SP)
- **Forecast:** Apr–Jun 2026 (Q2/2026)
- **Model:** Prophet (logistic growth + VN holidays, weekly_seasonality=True)

### Color Forecast → `prediction/color_q2.csv`
- Dùng tỷ trọng màu trung bình Q1-2026 nhân với Prophet yhat Q2

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
| Email pipeline | Python `email`, pdftotext (poppler) |
| Analytics / ML | pandas, scikit-learn (LogisticRegression), prophet |
| Dashboard | Dash 4.x / Plotly + Dash Bootstrap Components |
| Pipeline A (DB) | psycopg2, pdftotext (poppler) |
| Tests | pytest (21 tests analytics core) |
