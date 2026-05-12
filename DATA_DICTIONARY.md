# Data Dictionary — TNBike Analytics

Giải nghĩa toàn bộ cột trong các file CSV output.  
Xem cấu trúc tổng quan: [README.md](README.md)

---

## Nhóm BI / Phân tích — dùng `output/data/` và `agg_master.csv`

---

### `output/data/kpi_overview.csv`

| Cột | Giải nghĩa |
|---|---|
| `kpi` | Tên chỉ số: `total_revenue`, `total_orders`, `active_dealers`, `total_quantity`, `avg_order_value`, `sku_count`, `t3_orders_processed`, `t3_orders_failed`, `t3_success_rate` |
| `value` | Giá trị số |
| `unit` | Đơn vị: `VND`, `đại lý`, `đơn`, `%` |
| `period` | Kỳ áp dụng (vd: `Jan2025-Mar2026`) |

---

### `output/data/monthly_trend.csv`

Mỗi row = 1 tháng × 1 nhóm sản phẩm.

| Cột | Giải nghĩa |
|---|---|
| `fiscal_year / fiscal_month / fiscal_quarter` | Năm / tháng / quý |
| `ym` | `YYYY-MM` — dùng để sort |
| `group_code` | Mã nhóm SP: `CITYBIKE_P`, `KIDBIKE_1`, `KIDBIKE_2`, `SPORTBIKE_S`, `SPORTBIKE_A` |
| `group_name` | Tên nhóm SP tiếng Việt |
| `revenue` | Doanh thu (VND) |
| `quantity` | Số lượng xe (chiếc) |
| `n_orders` | Số đơn hàng |
| `n_customers` | Số đại lý đặt hàng |
| `yoy_revenue_pct` | % tăng trưởng so cùng kỳ năm trước (null nếu chưa đủ 12 tháng) |
| `mom_revenue_pct` | % tăng trưởng so tháng trước (null với tháng đầu tiên) |
| `cum_revenue_ytd` | Doanh thu lũy kế từ đầu năm |

---

### `output/data/geo_province.csv`

Mỗi row = 1 tỉnh thành. Dùng để vẽ bản đồ hoặc bar chart tỉnh.

| Cột | Giải nghĩa |
|---|---|
| `province_name` | Tên tỉnh |
| `region` | Vùng địa lý: `Miền Bắc`, `Miền Trung`, `Miền Nam`, … |
| `revenue` | Tổng doanh thu (VND) toàn kỳ |
| `quantity` | Tổng số lượng xe |
| `n_orders / n_customers` | Số đơn / số đại lý |
| `rev_pct_national` | Tỷ trọng DT so toàn quốc (%) |
| `rev_pct_region` | Tỷ trọng DT trong vùng (%) |
| `rank_national` | Xếp hạng quốc gia (1 = cao nhất) |
| `rank_in_region` | Xếp hạng trong vùng |

---

### `output/data/geo_region.csv`

Mỗi row = 1 vùng × 1 nhóm sản phẩm.

| Cột | Giải nghĩa |
|---|---|
| `region` | Tên vùng |
| `group_code / group_name` | Nhóm sản phẩm |
| `revenue / quantity / n_orders / n_customers` | Số liệu tổng hợp |

---

### `output/data/ops_pipeline.csv`

Kết quả vận hành pipeline email T3/2026.

| Cột | Giải nghĩa |
|---|---|
| `metric` | Tên chỉ số vận hành |
| `value` | Giá trị |
| `mo_ta` | Mô tả tiếng Việt |

---

### `output/data/ops_daily.csv`

Mỗi row = 1 ngày trong T3/2026.

| Cột | Giải nghĩa |
|---|---|
| `order_date` | Ngày (`YYYY-MM-DD`) |
| `n_orders` | Số đơn nhận ngày đó |
| `revenue` | Doanh thu ngày đó (VND) |

---

### `output/master/agg_master.csv` — File tổng hợp đa grain

Dùng cột `grain` để lọc đúng loại dữ liệu.  
⚠️ Đọc với `dtype={"product_code": str}` để giữ leading zero.

```python
df = pd.read_csv("output/master/agg_master.csv", dtype={"product_code": str})
monthly  = df[df.grain == "monthly_group"]
province = df[df.grain == "province_total"]
sku      = df[df.grain == "sku"]
customer = df[df.grain == "customer"]
forecast = df[df.grain == "forecast_daily"]
```

**Các giá trị `grain`:**

| `grain` | Dùng để vẽ |
|---|---|
| `monthly_group` | Line chart DT tháng × nhóm SP |
| `monthly_group_region` | Trend theo vùng × nhóm |
| `monthly_region / monthly_total` | Trend regional / KPI quốc gia |
| `province_total / province_group` | Bản đồ tỉnh / heatmap |
| `region_total / region_group` | Pie / stacked bar vùng |
| `national_group / national_total` | Bar summary tổng |
| `sku` | BCG bubble, Pareto, top SKU |
| `customer` | Churn table, RFM scatter |
| `forecast_daily` | Forecast band chart |

**Cột đặc thù grain `monthly_group`:**

| Cột | Giải nghĩa |
|---|---|
| `mom_revenue_pct` | % MoM |
| `yoy_revenue_pct` | % YoY |
| `revenue_share_pct` | Tỷ trọng nhóm SP |
| `cum_revenue_ytd` | Lũy kế YTD |

**Cột đặc thù grain `sku`:**

| Cột | Giải nghĩa |
|---|---|
| `product_code` | Mã SKU (string) |
| `revenue_2025 / revenue_2026` | DT năm 2025 / 2026 |
| `revenue_2026_ann` | DT 2026 annualized (× 12/tháng thực tế) |
| `yoy_revenue_pct_ann` | YoY annualized (%) |
| `avg_unit_price` | Giá bán trung bình |
| `revenue_rank` | Xếp hạng DT toàn SKU |
| `pareto_cum_pct` | % DT lũy kế Pareto |
| `pareto_class` | `A` (top 80% DT) / `B` (15%) / `C` (đuôi 5%) |
| `revenue_share_in_group_pct` | Tỷ trọng trong nhóm SP |
| `bcg_quadrant` | `Ngôi sao` / `Bò sữa` / `Dấu hỏi` / `Chó mực` |

**Cột đặc thù grain `customer`:**

| Cột | Giải nghĩa |
|---|---|
| `customer_code / customer_name` | Mã & tên đại lý |
| `cohort_month` | Tháng mua đầu tiên |
| `recency_days` | Ngày từ lần mua cuối đến 2026-03-31 |
| `avg_order_value` | Giá trị trung bình đơn (VND) |
| `n_product_groups` | Số nhóm SP đã mua |
| `trend_slope` | Hệ số xu hướng DT (+ = tăng, − = giảm) |
| `rfm_r / rfm_f / rfm_m` | RFM scores 1–5 (5 = tốt nhất) |
| `rfm_segment` | `Champions`, `Loyal`, `At Risk`, `Lost`, … |
| `churn_label` | `1` = churn (không mua 2026), `0` = active |
| `churn_prob` | Xác suất churn (0–1) |
| `churn_priority` | `Cao` / `Trung bình` / `Thấp` |
| `n_orders_q1_2026 / revenue_q1_2026` | Số đơn / DT Q1-2026 |

**Cột đặc thù grain `forecast_daily`:**

| Cột | Giải nghĩa |
|---|---|
| `ds` | Ngày dự báo |
| `yhat` | DT dự báo điểm (VND) |
| `yhat_lower / yhat_upper` | Khoảng tin cậy 95% |
| `y_actual` | Thực tế (null nếu tương lai) |
| `split` | `train` / `forecast` |
| `mae_test / mape_test_pct` | Sai số Prophet trên backtest |

---

## Nhóm ML / Dự báo — dùng `output/prediction/` và `fact_full.csv`

---

### `output/master/fact_full.csv` — Bảng fact (grain: order line)

Nguồn nền để build feature. Mỗi row = 1 dòng sản phẩm trong 1 đơn hàng.

**Cột giao dịch:**

| Cột | Giải nghĩa |
|---|---|
| `order_id` | ID đơn hàng |
| `so_number` | Số phiếu bán (`BH25.0001`) |
| `product_code` | Mã SKU — **đọc là string** |
| `quantity / unit_price / line_total` | SL / đơn giá / thành tiền |
| `order_date` | Ngày đặt hàng |
| `order_total` | Tổng giá trị đơn |
| `n_lines_in_order` | Số dòng SP trong đơn |
| `line_share_of_order_pct` | Tỷ trọng dòng trong đơn (%) |

**Cột thời gian:**

| Cột | Giải nghĩa |
|---|---|
| `fiscal_year / fiscal_month / fiscal_quarter` | Năm / tháng / quý |
| `ym / period_label / quarter_label` | Nhãn hiển thị |
| `day_of_week` | 0=Thứ Hai … 6=Chủ Nhật |
| `week_of_year` | Tuần ISO |
| `is_weekend` | 1 nếu Thứ 7/CN |

**Cột địa lý & sản phẩm:** `customer_code/name`, `province_name`, `region`, `product_name`, `color`, `line_name`, `group_code/name`

**Cột enrichment SKU** (tính toàn bộ kỳ — dùng cho phân tích, không dùng làm feature ML churn):

| Cột | Giải nghĩa |
|---|---|
| `sku_revenue_rank` | Xếp hạng DT SKU |
| `sku_pareto_class` | `A`/`B`/`C` |
| `sku_bcg_quadrant` | BCG quadrant |
| `sku_rev_share_group_pct` | Tỷ trọng trong nhóm (%) |
| `sku_yoy_rev_pct` | YoY doanh thu SKU (%) |
| `sku_avg_unit_price` | Giá bán trung bình |

**Cột enrichment đại lý** (feature period = Q1-2025 ≤ 2025-03-31):

> ⚠️ Chỉ dùng các cột `cust_*` làm feature ML — tính từ Q1-2025, không leak label 2026.

| Cột | Giải nghĩa |
|---|---|
| `cust_cohort_month` | Tháng mua đầu tiên |
| `cust_recency_days` | Ngày từ lần mua cuối đến 31/03/2025 |
| `cust_n_orders_q1_2025` | Số đơn Q1-2025 |
| `cust_revenue_q1_2025` | DT Q1-2025 (VND) |
| `cust_avg_order_value` | Giá trị trung bình đơn |
| `cust_rfm_r / f / m` | RFM scores 1–5 |
| `cust_rfm_segment` | Phân khúc RFM |
| `cust_churn_label` | `1` = churn (không mua 2026) |
| `cust_churn_prob / priority` | Xác suất churn / mức ưu tiên |

---

### `output/prediction/revenue_q2_daily.csv`

Prophet daily per nhóm SP — toàn bộ train + Q2 forecast.

| Cột | Giải nghĩa |
|---|---|
| `ds` | Ngày (`YYYY-MM-DD`) |
| `fiscal_year / fiscal_month` | Năm / tháng |
| `group_code` | Nhóm SP |
| `split` | `train` (lịch sử) / `forecast` (Q2-2026) |
| `yhat` | DT dự báo điểm (VND) |
| `yhat_lower / yhat_upper` | Khoảng tin cậy 95% |
| `y_actual` | Thực tế (null = tương lai) |
| `is_future` | `1` nếu Q2-2026 |

---

### `output/prediction/revenue_q2_monthly.csv`

Tổng hợp theo tháng (tháng × nhóm SP). Cột giống daily, thêm `ym`.

---

### `output/prediction/revenue_q2_weekly.csv`

Chỉ chứa Q2-2026, dùng để plan tồn kho tuần.

| Cột | Giải nghĩa |
|---|---|
| `yw` | Mã tuần ISO (`2026-W14` …) |
| `week_start` | Ngày đầu tuần (Thứ Hai) |
| `group_code` | Nhóm SP |
| `yhat / yhat_lower / yhat_upper` | DT tuần dự báo + khoảng tin cậy |

---

### `output/prediction/sku_q2_forecast.csv`

Phân bổ dự báo nhóm SP xuống SKU theo tỷ trọng lịch sử Q1.

| Cột | Giải nghĩa |
|---|---|
| `product_code` | Mã SKU (string) |
| `product_name / group_code` | Tên / nhóm |
| `fiscal_month / ym` | Tháng Q2 (4, 5, 6) |
| `predicted_revenue` | DT dự báo SKU (VND) |
| `predicted_revenue_lower / upper` | Khoảng tin cậy |
| `top20_flag` | `1` = top-20 SKU bán chạy nhất nhóm |
| `sku_share_in_group_pct` | Tỷ trọng SKU trong nhóm (%) — cơ sở phân bổ |

---

### `output/prediction/color_q2.csv`

Dự báo màu sắc Q2 + nhãn xu hướng mùa vụ.

| Cột | Giải nghĩa |
|---|---|
| `color / group_code` | Màu / nhóm SP |
| `fiscal_month / ym` | Tháng Q2 |
| `avg_share_q1_2026_pct` | Tỷ trọng màu Q1-2026 (%) — cơ sở tính |
| `group_yhat` | DT nhóm SP từ Prophet (VND) |
| `predicted_revenue` | DT màu = `group_yhat × avg_share / 100` |
| `seasonal_trend` | `Tăng nhu cầu` / `Giảm nhu cầu` / `Ổn định` |
| `yoy_share_chg` | Thay đổi tỷ trọng so cùng kỳ năm trước (pp) |

---

### `output/prediction/sku_cluster.csv`

K-Means k=4 phân loại SKU theo DT và tăng trưởng.

| Cột | Giải nghĩa |
|---|---|
| `product_code / product_name / group_code` | Định danh SKU |
| `revenue_2025 / revenue_2026` | DT năm (VND) |
| `yoy_revenue_pct` | YoY (%) |
| `revenue_rank` | Xếp hạng DT trong nhóm |
| `cluster` | Cluster K-Means (0–3) |
| `sku_cluster_label` | `Ngôi sao` / `Bò sữa` / `Dấu hỏi` / `Bán chậm` |
| `slow_mover_risk` | `Nguy cơ cao` / `Theo dõi` / `Ổn định` |

**Ý nghĩa cluster:**

| Label | Đặc điểm | Đề xuất |
|---|---|---|
| Ngôi sao | DT cao + YoY dương | Tăng tồn kho |
| Bò sữa | DT cao + YoY ổn định | Duy trì |
| Dấu hỏi | DT thấp + YoY dương | Theo dõi |
| Bán chậm | DT thấp + YoY âm | Giảm tồn kho / xem xét loại bỏ |

---

### `output/prediction/dealer_churn.csv`

LightGBM — 6 features Q1-2025 — ROC-AUC test = **0.843**

| Cột | Giải nghĩa |
|---|---|
| `customer_code` | Mã đại lý |
| `churn_label` | `1` = không mua lại 2026, `0` = tiếp tục |
| `churn_prob` | Xác suất churn dự báo (0–1) |
| `churn_priority` | `Cao` (≥0.6) / `Trung bình` (0.3–0.6) / `Thấp` (<0.3) |
| `churn_split` | `train` (80%) / `test` (20%) |
| `roc_auc_test` | ROC-AUC trên tập test |

**6 features không leakage:**

| Feature | SHAP rank | Ý nghĩa |
|---|---|---|
| `revenue_q1_2025` | 1 (0.533) | DT Q1-2025 |
| `recency_days` | 2 (0.200) | Ngày từ lần mua cuối đến 31/03/2025 |
| `n_product_groups` | 3 (0.189) | Số nhóm SP đã mua |
| `avg_order_value` | 4 (0.155) | Giá trị trung bình đơn |
| `trend_slope` | 5 (0.143) | Xu hướng DT |
| `n_orders_q1_2025` | 6 (0.082) | Số đơn Q1-2025 |

---

### `output/prediction/dealer_activity.csv`

BG-NBD — xác suất đặt hàng trong 30 ngày tới.

| Cột | Giải nghĩa |
|---|---|
| `customer_code` | Mã đại lý |
| `frequency` | Số lần mua lặp lại (= n_orders − 1) |
| `recency` | Ngày giữa lần mua đầu và cuối |
| `T` | Ngày từ lần mua đầu đến ngày quan sát |
| `prob_purchase_30d` | P(≥1 đơn trong 30 ngày tới) ∈ [0, 1] |
| `expected_orders_30d` | Số đơn kỳ vọng trong 30 ngày |
| `priority_contact` | `1` nếu `prob < 0.3` → cần chăm sóc gấp |
| `marketing_priority_label` | `Ưu tiên cao` / `Trung bình` / `Thấp` |
| `rfm_r / rfm_f / rfm_m` | RFM scores 1–5 |
| `rfm_segment` | Phân khúc RFM |
| `activity_risk` | `Nguy cơ cao` / `Trung bình` / `Tích cực` |

---

### `output/prediction/shap_importance.csv`

| Cột | Giải nghĩa |
|---|---|
| `feature` | Tên feature LightGBM |
| `shap_mean_abs` | SHAP mean \|absolute\| — đo đóng góp trung bình |
| `rank` | 1 = quan trọng nhất |
