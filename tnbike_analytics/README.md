# 🚲 tnbike_analytics — DATA EXPLORERS 2026 Vòng 2

Hệ thống phân tích dữ liệu kinh doanh cho **Công ty Xe đạp Thống Nhất**  
Phạm vi dữ liệu: 02/01/2025 – 31/03/2026 | 702 đại lý | 247 SKU | 5 nhóm sản phẩm

---

## Cấu trúc dự án

```
tnbike_analytics/
├── config.py                    # Cấu hình DB, đường dẫn, hằng số nghiệp vụ
├── requirements.txt
├── .env.example
│
├── pipeline/                    # HẠNG MỤC A — Xử lý email + PDF
│   ├── email_parser.py          # Parse .eml, trích xuất metadata + PDF attachment
│   ├── pdf_extractor.py         # Parse PDF đặt hàng qua pdftotext (poppler)
│   ├── validator.py             # Kiểm tra hợp lệ trước khi ghi DB
│   ├── db_connection.py         # PostgreSQL connection context manager
│   ├── db_writer.py             # Ghi email_log → sales_order → order_line → fact_sales
│   └── run_pipeline.py          # Entry point: xử lý 1.132 email T3/2026
│
├── analytics/                   # HẠNG MỤC B — Phân tích
│   ├── kpi_calculator.py        # 6 nhóm KPI: sản lượng, doanh thu, tăng trưởng...
│   ├── rfm_analysis.py          # RFM scoring + churn detection cho 702 đại lý
│   ├── bcg_matrix.py            # BCG Matrix phân loại 5 nhóm SP
│   ├── market_basket.py         # Apriori association rules
│   ├── geographic_analysis.py   # Phân tích địa lý 63 tỉnh / 3 miền
│   └── forecasting/             # HẠNG MỤC C — Dự báo
│       ├── demand_forecast.py   # Prophet dự báo doanh số Q2/2026 theo nhóm SP
│       ├── color_forecast.py    # Dự báo màu sắc/SKU Q2/2026
│       └── dealer_forecast.py   # Churn prediction (Logistic/RF/GBM)
│
├── dashboard/
│   ├── app.py                   # Streamlit app — 6 màn hình BI
│   └── config.py                # Màu sắc, nhãn cho charts
│
├── sql/
│   ├── 01_create_tables.sql     # Schema gốc (9 tables + 4 views + triggers)
│   ├── 02_import_data.sql       # Dữ liệu 2025–T2/2026
│   ├── 03_email_log.sql         # Bảng log pipeline A
│   ├── 04_dim_date.sql          # Dimension ngày (mùa vụ VN)
│   └── 05_views_extra.sql       # Views: pipeline_summary, churn_candidates
│
├── tests/
│   ├── test_email_parser.py
│   ├── test_pdf_extractor.py
│   └── test_validator.py
│
└── data/
    ├── raw/emails/              # 1.132 file .eml T3/2026
    ├── raw/pdfs/                # 1.132 file .pdf T3/2026
    └── processed/               # pipeline_result.json, pipeline.log
```

---

## Cài đặt

```bash
# 1. Tạo môi trường ảo
python -m venv .venv && source .venv/bin/activate

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Cài poppler (cần cho pdf_extractor)
apt-get install -y poppler-utils   # Ubuntu/Debian

# 4. Cấu hình DB
cp .env.example .env
# Sửa .env với thông tin PostgreSQL thực tế

# 5. Khởi tạo DB
psql -U postgres -d tnbike_db -f sql/01_create_tables.sql
psql -U postgres -d tnbike_db -f sql/02_import_data.sql
psql -U postgres -d tnbike_db -f sql/03_email_log.sql
psql -U postgres -d tnbike_db -f sql/04_dim_date.sql
psql -U postgres -d tnbike_db -f sql/05_views_extra.sql
```

---

## Chạy Pipeline A

```bash
# Copy dữ liệu email và PDF vào đúng thư mục
cp /path/to/emails/*.eml data/raw/emails/
cp /path/to/pdfs/*.pdf   data/raw/pdfs/

# Chạy pipeline
python -m pipeline.run_pipeline --email-dir data/raw/emails --pdf-dir data/raw/pdfs

# Kết quả ghi vào data/processed/pipeline_result.json
```

**Output mẫu:**
```json
{
  "tong_file": 1132,
  "thanh_cong": 1089,
  "ti_le_thanh_cong": 96.2,
  "loi_invalid": 43,
  "canh_bao": 27,
  "thoi_gian_tb_giay": 0.15
}
```

---

## Chạy Dashboard

```bash
streamlit run dashboard/app.py
```

Mở trình duyệt tại http://localhost:8501

**6 màn hình:**
1. **① Tổng quan kinh doanh** — KPI cards + trend line + pie chart nhóm SP + pipeline funnel
2. **② Phân tích thời gian** — Xu hướng theo tháng, so sánh cùng kỳ, phân tích mùa vụ
3. **③ Phân tích sản phẩm** — 3 cấp phân tích, BCG Matrix, heatmap màu sắc, co-purchase
4. **④ Phân tích đại lý** — RFM scatter, Top/Bottom dealers, Pareto, churn risk list
5. **⑤ Phân tích địa lý** — Bar chart tỉnh, Treemap, so sánh 3 miền theo quý, tăng trưởng
6. **⑥ Trạng thái vận hành** — KPI pipeline, donut chart, chi tiết lỗi

---

## Chạy Tests

```bash
python -m pytest tests/ -v
```

---

## Schema tnbike

| Bảng | Mô tả |
|---|---|
| `product_group` | 5 nhóm sản phẩm cấp 1 |
| `product_line` | 72 dòng xe cấp 3 |
| `product` | 247 SKU (mã hàng × màu sắc) |
| `product_price` | Lịch sử giá |
| `province` | 63 tỉnh thành |
| `customer` | 702 đại lý |
| `sales_order` | Đầu phiếu bán hàng |
| `order_line` | Dòng hàng hóa |
| `fact_sales` | Bảng fact phẳng cho analytics |
| `email_log` | Log xử lý pipeline A |
| `dim_date` | Dimension ngày (mùa vụ VN) |

**5 nhóm sản phẩm:**
- `CITYBIKE_P` — Xe phổ thông
- `KIDBIKE_1` — Xe trẻ em nhóm 1 (bánh ≤ 20")
- `KIDBIKE_2` — Xe trẻ em nhóm 2 (bánh 12–16")
- `SPORTBIKE_S` — Xe thể thao khung thép
- `SPORTBIKE_A` — Xe thể thao khung nhôm

---

## Công nghệ

| Layer | Công nghệ |
|---|---|
| Database | PostgreSQL 14+ |
| ETL / Pipeline | Python 3.11, psycopg2, pdftotext (poppler) |
| Analytics | pandas, scikit-learn, mlxtend, prophet |
| Dashboard | Streamlit, Plotly |
| Tests | pytest |
