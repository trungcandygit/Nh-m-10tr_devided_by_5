# Kết quả kiểm thử prediction_engine.py

Ngày chạy: 2026-05-12 03:16

## Q1 — Prophet Forecast

| Chỉ số | Giá trị |
|---|---|
| Số nhóm SP | 5 |
| Daily rows (train+forecast) | 924 |
| Monthly rows | 45 |
| Weekly rows (Q2 only) | 70 |
| SKU Q2 total rows | 363 |
| Top-20 SKU (flag=1) | 60 |
| yhat âm | 0 |

## Q2 — Color Demand + K-Means

| Chỉ số | Giá trị |
|---|---|
| Color Q2 rows | 180 |
| SKU cluster rows | 161 |
| Slow-mover (Nguy cơ cao) | 79 |
| Theo dõi | 0 |
| Seasonal trend — Tăng | 2 màu |
| Seasonal trend — Giảm | 2 màu |
| Seasonal trend — Ổn định | 2 màu |

### Phân bổ cluster SKU

| Cluster | Số SKU |
|---|---|
| Bán chậm | 76 |
| Bò sữa | 74 |
| Ngôi sao | 9 |
| Dấu hỏi | 2 |

## Q3 — BG-NBD + LightGBM Churn + SHAP

| Chỉ số | Giá trị |
|---|---|
| Đại lý phân tích | 333 |
| BG-NBD prob_purchase_30d — mean | 0.293 |
| BG-NBD prob_purchase_30d — median | 0.010 |
| priority_contact=1 (prob < 0.3) | 281 |
| LightGBM ROC-AUC (test 20%) | **0.843** |
| Churn cao (P ≥ 0.6) | 302 |
| Churn trung bình (0.3–0.6) | 29 |
| Churn thấp (P < 0.3) | 2 |

### SHAP Feature Importance (LightGBM Churn)

| Rank | Feature | SHAP mean |abs| |
|---|---|---|
| 1 | revenue_q1_2025 | 0.5333 |
| 2 | recency_days | 0.2003 |
| 3 | n_product_groups | 0.1893 |
| 4 | avg_order_value | 0.1550 |
| 5 | trend_slope | 0.1428 |
| 6 | n_orders_q1_2025 | 0.0818 |

### Phân bổ phân khúc RFM

| Phân khúc | Số đại lý |
|---|---|
| Có nguy cơ rời bỏ | 107 |
| Cần theo dõi | 82 |
| Khách hàng tiêu biểu | 54 |
| Khách hàng mới tiềm năng | 44 |
| Cần chăm sóc đặc biệt | 27 |
| Khách hàng trung thành | 19 |

### Marketing Priority

| Mức | Số đại lý |
|---|---|
| Ưu tiên cao | 302 |
| Trung bình | 31 |