# Xe Đạp Thống Nhất — Hệ Thống Phân Tích Dữ Liệu Bán Hàng TNBike

> **Báo cáo học thuật — 8 Dự Án Khoa Học Dữ Liệu Ứng Dụng**  
> Dữ liệu: `tnbike_db` | Giai đoạn: 2025 Q1 – 2026 Q1 | Tổng giao dịch: 17,031

---

## Mục Lục

1. [Tổng Quan Dự Án](#1-tổng-quan-dự-án)
2. [Kiến Trúc Dữ Liệu](#2-kiến-trúc-dữ-liệu)
3. [Cài Đặt & Kết Nối](#3-cài-đặt--kết-nối)
4. [Dự Án 1 — Khám Phá & Làm Sạch Dữ Liệu](#4-dự-án-1--khám-phá--làm-sạch-dữ-liệu)
5. [Dự Án 2 — Dự Đoán Doanh Thu (Ridge Regression)](#5-dự-án-2--dự-đoán-doanh-thu-ridge-regression)
6. [Dự Án 3 — Dự Báo Chuỗi Thời Gian (AR/ARMA)](#6-dự-án-3--dự-báo-chuỗi-thời-gian-ararmac2)
7. [Dự Án 4 — Phân Loại Đơn Hàng Giá Trị Cao](#7-dự-án-4--phân-loại-đơn-hàng-giá-trị-cao)
8. [Dự Án 5 — Phát Hiện Churn Đại Lý (Random Forest)](#8-dự-án-5--phát-hiện-churn-đại-lý-random-forestc2)
9. [Dự Án 6 — Phân Nhóm Khách Hàng RFM](#9-dự-án-6--phân-nhóm-khách-hàng-rfm)
10. [Dự Án 7 — AB Testing Chiến Dịch Bán Hàng](#10-dự-án-7--ab-testing-chiến-dịch-bán-hàng)
11. [Dự Án 8 — Dự Báo Biến Động Doanh Thu GARCH](#11-dự-án-8--dự-báo-biến-động-doanh-thu-garch)
12. [Câu Hỏi Thi C.2 — Ba Dự Báo Chính](#12-câu-hỏi-thi-c2--ba-dự-báo-chính)
13. [Hướng Dẫn Chạy](#13-hướng-dẫn-chạy)

---

## 1. Tổng Quan Dự Án

Hệ thống gồm **8 dự án độc lập** được xây dựng theo cấu trúc WQU Applied Data Science Lab, áp dụng trực tiếp vào dữ liệu kinh doanh thực tế của Công ty Xe đạp Thống Nhất (TNBike). Mỗi dự án giải quyết một bài toán kinh doanh cụ thể, từ phân tích mô tả đến dự báo và phân loại.

| # | Dự Án | Phương Pháp | Bài Toán Kinh Doanh |
|---|-------|-------------|---------------------|
| 1 | Khám Phá & Làm Sạch | EDA, IQR | Hiểu phân phối doanh thu, phát hiện ngoại lệ |
| 2 | Dự Đoán Doanh Thu | Ridge Regression | Dự báo doanh thu theo đặc trưng sản phẩm |
| 3 | Chuỗi Thời Gian | AR, ARMA, Walk-Forward | Dự báo doanh số Q2/2026 |
| 4 | Phân Loại Đơn Hàng | Logistic Regression, Decision Tree | Xác định đơn hàng giá trị cao |
| 5 | Phát Hiện Churn | Random Forest, GridSearchCV | Dự báo đại lý có nguy cơ ngừng mua |
| 6 | Phân Nhóm Khách Hàng | KMeans, PCA | Phân khúc khách hàng theo RFM |
| 7 | AB Testing | Chi-square, Table2x2 | Đánh giá hiệu quả chiến dịch marketing |
| 8 | Biến Động Doanh Thu | GARCH(p,q) | Mô hình hoá và dự báo rủi ro doanh thu |

---

## 2. Kiến Trúc Dữ Liệu

### Schema: `tnbike` (PostgreSQL / Neon Cloud)

```
fact_sales          — Bảng fact phẳng (denormalized), 17,031 dòng
  ├── order_date, fiscal_year, fiscal_quarter, fiscal_month
  ├── so_number, customer_code, customer_name
  ├── province_name, region
  ├── product_code, product_name, color, line_name, group_name
  ├── quantity, unit_price (Triệu VNĐ), line_total (Triệu VNĐ)

sales_order         — Đơn bán hàng
order_line          — Chi tiết dòng hàng
product             — Danh mục sản phẩm (có trường color)
product_line        — Dòng sản phẩm
product_group       — Nhóm sản phẩm (5 nhóm)
product_price       — Lịch sử giá niêm yết
customer            — Thông tin đại lý
province            — Tỉnh/thành, vùng miền
email_don_hang      — 1,132 email đặt hàng tháng 3/2026 (parsed)

Views:
  v_monthly_by_group  — Doanh số tháng theo nhóm SP
  v_customer_period   — Hành vi mua hàng theo kỳ
  v_sku_monthly       — Doanh số SKU x màu x tháng
  v_customer_activity — Hoạt động đại lý
```

### Đơn Vị

- `unit_price`, `line_total`: **Triệu VNĐ** (đã chia `/1,000,000`, làm tròn 2 chữ số)
- `quantity`: chiếc
- Doanh thu tổng hợp: **Triệu VNĐ/ngày** hoặc **Triệu VNĐ/quý**

---

## 3. Cài Đặt & Kết Nối

### Yêu Cầu

```
Python >= 3.11
```

### Cài Thư Viện

```bash
pip install -r requirements.txt
```

### Kết Nối Database

Tất cả notebook dùng chung connection string:

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://neondb_owner:npg_kyw0DxEUvMK7"
    "@ep-little-fog-aprabc8e.c-7.us-east-1.aws.neon.tech"
    "/neondb?sslmode=require"
)
```

### Clone & Chạy

```bash
git clone https://github.com/trungcandygit/Nh-m-10tr_devided_by_5.git
cd Nh-m-10tr_devided_by_5
pip install -r requirements.txt
# Mở JupyterLab, chạy từng notebook theo thứ tự
```

---

## 4. Dự Án 1 — Khám Phá & Làm Sạch Dữ Liệu

**Notebook:** `1. Kham Pha Du Lieu Ban Hang TNBike/02_lam_sach_du_lieu.ipynb`

### Mục Tiêu

Hiểu cấu trúc dữ liệu bán hàng, xác định phân phối, phát hiện và xử lý ngoại lệ trước khi đưa vào mô hình.

### Phương Pháp

```python
def wrangle(engine):
    # Tải từ fact_sales (2025-01 đến 2026-03)
    # Loại bỏ ngoại lệ: giữ quantile [10%, 90%]
    thap, cao = df['line_total'].quantile([0.10, 0.90])
    df = df[df['line_total'].between(thap, cao)]
    return df
```

### Phân Tích

- Phân phối `line_total`: lệch phải, cần xử lý ngoại lệ
- Tương quan `quantity` ~ `line_total` theo tỉnh/thành
- Top 10 tỉnh/thành doanh thu cao nhất
- Doanh thu trung bình theo nhóm sản phẩm và vùng miền

---

## 5. Dự Án 2 — Dự Đoán Doanh Thu (Ridge Regression)

**Notebook:** `2. Du Doan Doanh Thu San Pham/03_mo_hinh_hoi_quy.ipynb`

### Phương Trình Mô Hình

$$\hat{y} = \beta_0 + \beta_1 X_{quantity} + \beta_2 X_{unit\_price} + \beta_3 X_{fiscal\_month} + \sum_{k} \beta_k X_{line\_name_k} + \varepsilon$$

Trong đó $\hat{y}$ = doanh thu dự báo (Triệu VNĐ), với **điều chuẩn hóa L2** (Ridge):

$$\min_{\beta} \left[ \sum_{i=1}^{n}(y_i - \hat{y}_i)^2 + \alpha \sum_{j=1}^{p} \beta_j^2 \right]$$

### Pipeline

```python
from sklearn.pipeline import make_pipeline
from category_encoders import OneHotEncoder
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

mo_hinh = make_pipeline(
    OneHotEncoder(use_cat_names=True),
    StandardScaler(),
    Ridge()
)
```

### Đặc Trưng Đầu Vào

| Đặc Trưng | Kiểu | Mô Tả |
|-----------|------|--------|
| `quantity` | Số | Số lượng sản phẩm |
| `unit_price` | Số | Đơn giá (Triệu VNĐ) |
| `fiscal_month` | Số | Tháng tài chính (1-12) |
| `region` | Phân loại | Miền Bắc/Trung/Nam |
| `group_name` | Phân loại | Nhóm xe (5 nhóm) |
| `line_name` | Phân loại | Dòng xe |
| `color` | Phân loại | Màu sắc sản phẩm |

### Chỉ Tiêu Hiệu Quả

| Chỉ Tiêu | Ý Nghĩa |
|----------|---------|
| **MAE** | Sai số tuyệt đối trung bình (Triệu VNĐ) |
| **RMSE** | Căn bậc hai sai số bình phương |
| **R²** | Hệ số xác định (0–1, càng cao càng tốt) |
| **MAPE** | Sai số phần trăm tuyệt đối trung bình |

### Câu Hỏi C.2 — Dự Báo Màu Sắc Q2/2026

- Màu sắc nào tăng nhu cầu theo mùa vụ Q2/Q1
- Cơ cấu tỷ trọng màu sắc dự kiến Q2/2026
- SKU có dấu hiệu nhu cầu giảm (tăng trưởng < -10% so cùng kỳ)

**Phương pháp:** Hệ số mùa vụ = `SUM(Q2_2025) / SUM(Q1_2025)` nhân với thực tế Q1/2026

---

## 6. Dự Án 3 — Dự Báo Chuỗi Thời Gian AR/ARMA (C.2)

**Notebook:** `3. Phan Tich Chuoi Thoi Gian Doanh So/03_mo_hinh_ar_arma.ipynb`

### Phương Trình Mô Hình AR(p)

$$\hat{y}_t = \phi_1 y_{t-1} + \phi_2 y_{t-2} + \cdots + \phi_p y_{t-p} + \varepsilon_t$$

Trong đó:
- $\phi_k$ = hệ số tự hồi quy lag thứ k
- $y_{t-k}$ = doanh thu ngày $t-k$ (Triệu VNĐ)
- $\varepsilon_t \sim \mathcal{N}(0, \sigma^2)$ = nhiễu trắng

### So Sánh Mô Hình

| Mô Hình | Lags | Tiêu Chí Chọn |
|---------|------|---------------|
| AR(1) | 1 | Baseline |
| AR(7) | 7 | Chu kỳ tuần |
| AR(14) | 14 | Chu kỳ 2 tuần |
| **AR(p*)** | **Tối ưu** | **AIC nhỏ nhất** |

### Walk-Forward Validation

```
Train: 90% đầu  |  Test: 10% cuối
Mỗi bước: train → predict 1 ngày → thêm vào train → lặp lại
```

### Câu Hỏi C.2 — Dự Báo Doanh Số Q2/2026

1. **Tổng doanh thu tháng 4, 5, 6/2026** (Triệu VNĐ)
2. **Dự báo theo tuần** trong Q2/2026
3. **Dự báo theo nhóm sản phẩm** (AR riêng cho 5 nhóm)
4. **Top 20 SKU bán chạy nhất Q2/2026** (dùng hệ số mùa vụ Q2/Q1-2025)

---

## 7. Dự Án 4 — Phân Loại Đơn Hàng Giá Trị Cao

**Notebook:** `4. Phan Loai Don Hang Gia Tri Cao/02_phan_loai.ipynb`

### Biến Mục Tiêu

```python
nguong = df['doanh_thu'].quantile(0.75)   # Ngưỡng 75th percentile
df['gia_tri_cao'] = (df['doanh_thu'] > nguong).astype(int)
```

### So Sánh Mô Hình Phân Loại

| Mô Hình | Ưu Điểm | Nhược Điểm |
|---------|---------|------------|
| Logistic Regression | Giải thích được, nhanh | Giả định tuyến tính |
| Decision Tree | Trực quan, dễ hiểu | Dễ overfit |

### Chỉ Tiêu Đánh Giá

- **Confusion Matrix**: TP, FP, TN, FN
- **Validation Curve**: Bias-Variance tradeoff theo `max_depth`
- **Classification Report**: Precision, Recall, F1 theo từng lớp

---

## 8. Dự Án 5 — Phát Hiện Churn Đại Lý (Random Forest) (C.2)

**Notebook:** `5. Phat Hien Churn Dai Ly/02_mo_hinh_random_forest.ipynb`

### Định Nghĩa Churn

```python
moc = pd.Timestamp('2025-09-30')
df['churn'] = (df['ngay_mua_cuoi'] < moc).astype(int)
# Churn = 1 nếu đại lý không mua hàng sau 30/09/2025
```

### Phương Trình Random Forest

$$\hat{P}(\text{churn}) = \frac{1}{T} \sum_{t=1}^{T} h_t(X)$$

$$\text{Feature Importance}(X_j) = \frac{1}{T} \sum_{t=1}^{T} \sum_{n \in h_t} p(n) \cdot \Delta I(n, X_j)$$

Trong đó $T$ = số cây, $h_t$ = cây thứ t, $\Delta I$ = độ giảm impurity

### Xử Lý Mất Cân Bằng Lớp

```python
from imblearn.over_sampling import RandomOverSampler
over_sampler = RandomOverSampler(random_state=42)
X_train_over, y_train_over = over_sampler.fit_resample(X_train, y_train)
```

### Tối Ưu Siêu Tham Số

```python
tham_so = {
    'simpleimputer__strategy': ['mean', 'median'],
    'randomforestclassifier__n_estimators': [25, 50, 75],
    'randomforestclassifier__max_depth': [10, 20, None]
}
mo_hinh = GridSearchCV(clf, tham_so, cv=5, scoring='accuracy')
```

### Câu Hỏi C.2 — Dự Báo 30 Ngày

- `predict_proba()` → xác suất churn từng đại lý
- **Ranked list** nguy cơ cao: xac_suat_churn >= 60%
- **Điểm xu hướng mua hàng** = f(số ngày im lặng, số đơn, doanh thu)
- **Mức ưu tiên tiếp thị**: Khẩn Cấp (>=70%) / Theo Dõi (50-70%) / Ổn Định (<50%)

---

## 9. Dự Án 6 — Phân Nhóm Khách Hàng RFM

**Notebook:** `6. Phan Nhom Khach Hang RFM/03_dashboard.ipynb`

### Ma Trận Đặc Trưng RFM

| Đặc Trưng | Ký Hiệu | Công Thức |
|-----------|---------|-----------|
| Recency | R | `CURRENT_DATE - MAX(order_date)` |
| Frequency | F | `COUNT(DISTINCT so_number)` |
| Monetary | M | `SUM(line_total)` (Triệu VNĐ) |

### Thuật Toán KMeans

$$\min_{C_1,...,C_k} \sum_{k=1}^{K} \sum_{x_i \in C_k} \|x_i - \mu_k\|^2$$

Số cụm **k = 3** được chọn dựa trên **Elbow Method** và **Silhouette Score**.

### Giảm Chiều PCA

$$Z = XV \quad \text{(2 thành phần chính)}$$

PC1 và PC2 giải thích tối đa phương sai — dùng để trực quan hoá cụm 2D.

### Dashboard Tương Tác

- `ipywidgets.IntSlider`: chọn cụm (0, 1, 2) để xem thống kê chi tiết
- Biểu đồ phân bố vùng miền theo cụm
- Tán xạ PCA 2D có màu theo cụm

---

## 10. Dự Án 7 — AB Testing Chiến Dịch Bán Hàng

**Notebook:** `7. AB Testing Chien Dich Ban Hang/03_phan_tich_ab.ipynb`

### Dữ Liệu Email

1,132 email đặt hàng tháng 3/2026 (file `tnbike_emails_mar2026.rar`) được parse và lưu vào bảng `tnbike.email_don_hang`:

```
so_bh | ngay_don | dai_ly | mst | dia_chi | so_san_pham | tong_chiec | tri_gia_dong
```

### Kiểm Định Thống Kê

**Giả thuyết:**
- H₀: Chiến dịch marketing không ảnh hưởng đến tỷ lệ đặt hàng
- H₁: Chiến dịch marketing làm tăng tỷ lệ đặt hàng

**Phương pháp:**

```python
from statsmodels.stats.contingency_tables import Table2x2
from statsmodels.stats.power import GofChisquarePower

# Chi-square test
# Odds Ratio, Risk Ratio
# Statistical Power >= 0.8
```

### Phân Tích Theo Tỉnh/Thành

- Choropleth map phân bố đại lý tham gia chiến dịch
- So sánh conversion rate theo vùng miền

---

## 11. Dự Án 8 — Dự Báo Biến Động Doanh Thu GARCH

**Notebook:** `8. Du Bao Bien Dong Doanh Thu GARCH/04_du_bao.ipynb`

### Chuỗi Lợi Suất

```python
df['loi_suat'] = df['daily_revenue'].pct_change() * 100
# Kiểm định ARCH effect: ACF của loi_suat^2
```

### Phương Trình GARCH(p,q)

**Mean equation:**
$$r_t = \mu + \varepsilon_t, \quad \varepsilon_t = \sigma_t z_t$$

**Variance equation:**
$$\sigma_t^2 = \omega + \sum_{i=1}^{q} \alpha_i \varepsilon_{t-i}^2 + \sum_{j=1}^{p} \beta_j \sigma_{t-j}^2$$

Trong đó:
- $\omega > 0$: hằng số phương sai dài hạn
- $\alpha_i$: hệ số ARCH (ảnh hưởng của shock quá khứ)
- $\beta_j$: hệ số GARCH (tính dai dẳng của biến động)

### Lựa Chọn Mô Hình

| Mô Hình | AIC | BIC | Chọn |
|---------|-----|-----|------|
| GARCH(1,1) | — | — | Baseline |
| GARCH(1,2) | — | — | — |
| GARCH(2,1) | — | — | — |
| **GARCH(p*,q*)** | **Thấp nhất** | **Thấp nhất** | **Chọn** |

### Dự Báo 5 Ngày

```python
du_bao_bien_dong = mo_hinh_garch.forecast(horizon=5)
# Lưu mô hình: joblib.dump(mo_hinh_garch, 'mo_hinh_garch.pkl')
```

---

## 12. Câu Hỏi Thi C.2 — Ba Dự Báo Chính

### Câu Hỏi 1 — Dự Báo Doanh Số Q2/2026

**Vị trí:** `3. Phan Tich Chuoi Thoi Gian Doanh So/03_mo_hinh_ar_arma.ipynb` → Mục "Câu Hỏi 1 (C.2)"

| Đầu Ra | Mô Tả |
|--------|-------|
| Tổng doanh thu tháng 4/2026 | Triệu VNĐ |
| Tổng doanh thu tháng 5/2026 | Triệu VNĐ |
| Tổng doanh thu tháng 6/2026 | Triệu VNĐ |
| Dự báo theo tuần | 13 tuần Q2 |
| Dự báo theo nhóm SP | 5 nhóm riêng biệt |
| Top 20 SKU bán chạy | Số lượng + doanh thu |

### Câu Hỏi 2 — Phân Tích Màu Sắc Q2/2026

**Vị trí:** `2. Du Doan Doanh Thu San Pham/03_mo_hinh_hoi_quy.ipynb` → Mục "Câu Hỏi 2 (C.2)"

| Đầu Ra | Mô Tả |
|--------|-------|
| Xu hướng tỷ trọng màu theo quý | Biểu đồ line chart |
| Cơ cấu màu sắc dự báo Q2/2026 | Tỷ lệ % theo màu |
| SKU nguy cơ bán chậm | Tăng trưởng < -10% YoY |

### Câu Hỏi 3 — Đại Lý Có Nguy Cơ Churn 30 Ngày

**Vị trí:** `5. Phat Hien Churn Dai Ly/02_mo_hinh_random_forest.ipynb` → Mục "Câu Hỏi 3 (C.2)"

| Đầu Ra | Mô Tả |
|--------|-------|
| Xác suất churn từng đại lý | `predict_proba()` |
| Danh sách ranked theo nguy cơ | Sắp xếp giảm dần |
| Điểm xu hướng mua hàng | 0–100 |
| Mức ưu tiên tiếp thị | Khẩn Cấp / Theo Dõi / Ổn Định |

---

## 13. Hướng Dẫn Chạy

### Thứ Tự Chạy Để Show Giám Khảo

```
Bước 1: clone + install
  git clone https://github.com/trungcandygit/Nh-m-10tr_devided_by_5.git
  pip install -r requirements.txt

Bước 2: Mở JupyterLab, chạy theo thứ tự
  1. Kham Pha.../02_lam_sach_du_lieu.ipynb        → EDA + wrangle
  2. Du Doan.../03_mo_hinh_hoi_quy.ipynb          → Ridge + C.2 Cau 2
  3. Phan Tich.../03_mo_hinh_ar_arma.ipynb        → AR + C.2 Cau 1
  4. Phan Loai.../02_phan_loai.ipynb              → Classification
  5. Phat Hien.../02_mo_hinh_random_forest.ipynb  → RF + C.2 Cau 3
  6. Phan Nhom.../03_dashboard.ipynb              → KMeans + dashboard
  7. AB Testing.../03_phan_tich_ab.ipynb          → Chi-square
  8. Du Bao GARCH.../04_du_bao.ipynb              → GARCH

Bước 3: Kernel → Restart & Run All mỗi notebook
```

### Xuất PDF Sau Khi Chạy

```python
# Chạy trong JupyterLab terminal sau khi execute xong
import subprocess, glob
for nb in glob.glob("**/*.ipynb", recursive=True):
    subprocess.run(["jupyter", "nbconvert", "--to", "pdf", nb])
```

### Lưu Ý

- Tất cả notebook dùng chung 1 connection string (Neon cloud)
- Không cần cài PostgreSQL local
- `plotly` dùng renderer `iframe` — hiển thị đúng trên JupyterLab cloud
- Đơn vị tiền tệ: **Triệu VNĐ** (đã chuẩn hoá trong SQL)

---

## Công Nghệ Sử Dụng

```
PostgreSQL (Neon Cloud)  — Cơ sở dữ liệu
SQLAlchemy               — ORM & connection
pandas / numpy           — Xử lý dữ liệu
scikit-learn             — ML models
statsmodels / arch       — Time series & GARCH
imbalanced-learn         — RandomOverSampler
matplotlib / seaborn     — Visualization tĩnh
plotly                   — Visualization tương tác
ipywidgets               — Dashboard non-tech
category_encoders        — OneHotEncoder
```

---

*Dự án phát triển theo cấu trúc WorldQuant University Applied Data Science Lab — áp dụng vào dữ liệu thực tế TNBike.*
