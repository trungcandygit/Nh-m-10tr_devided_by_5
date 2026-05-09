# CLAUDE.md — tnbike_analytics

## Chart Style Reference

All chart notebooks: `./_chart_refs/src/notebooks/`
Preview images: `./_chart_refs/static/graph/`
Style helper: `./chart_style.py`

## Quy tắc BẮT BUỘC khi vẽ chart

1. Import `chart_style.py` và gọi `apply_gallery_style(ax)` cho mọi axes
2. Tìm notebook phù hợp trong `_chart_refs/src/notebooks/` trước khi code
3. Copy y hệt: màu sắc, font, padding, grid style từ notebook mẫu
4. Tất cả nhãn/tiêu đề/chú thích phải bằng **tiếng Việt**
5. DPI=300, bbox_inches="tight", facecolor="white"
6. Output: `output/charts/*.png` và `output/tables/*.xlsx`

## Mapping chart → notebook mẫu

| Muốn vẽ | Đọc notebook |
|---|---|
| Multi-line với nhãn cuối | `web-line-chart-with-labels-at-line-end.ipynb` |
| Horizontal bar (Economist) | `web-horizontal-barplot-with-labels-the-economist.ipynb` |
| Stacked area | `243-area-chart-with-white-grid.ipynb` |
| Bubble / Scatter | `web-bubble-plot-with-annotations-and-custom-features.ipynb` |
| Heatmap | `91-customize-seaborn-heatmap.ipynb` |
| Donut | `161-custom-matplotlib-donut-plot.ipynb` |
| Lollipop | `web-lollipop-plot-with-python-the-office.ipynb` |
| Dual Y-axis | `line-chart-dual-y-axis-with-matplotlib.ipynb` |
| Area với fill | `web-area-chart-with-different-colors-for-positive-and-negative-values.ipynb` |
| Grouped bar | `11-grouped-barplot.ipynb` |
| Forecast band | `web-area-chart-with-different-colors-for-positive-and-negative-values.ipynb` |

## Màu sắc thương hiệu tnbike

```python
BRAND_COLORS = {
    "CITYBIKE_P":  "#1D9E75",   # xanh lá
    "KIDBIKE_1":   "#378ADD",   # xanh dương
    "KIDBIKE_2":   "#7F77DD",   # tím
    "SPORTBIKE_S": "#D85A30",   # cam đỏ
    "SPORTBIKE_A": "#BA7517",   # vàng nâu
}
```

## Gallery style chuẩn

```python
# Background
BG_WHITE  = "#fafaf5"
BG_AXES   = "#f8f8f8"

# Grid
GRID_COLOR = "#FFFFFF"  # trắng trên nền xám
GRID_ALPHA = 0.8

# Spines: xóa top + right, giữ left (lw=1.5)
# tick_params: length=0
# Title: fontsize=14, fontweight="bold", loc="left"
# Watermark: "Xe đạp Thống Nhất • DATA EXPLORERS 2026"
```

## Cấu trúc dữ liệu

- `sql_data_loader.load_all()` → dict DataFrames từ SQL không cần DB
- `sql_data_loader.build_fact()` → bảng fact phẳng 17,031 dòng
- Cột quan trọng: `order_date`, `fiscal_year`, `fiscal_month`, `fiscal_quarter`,
  `group_code`, `product_code`, `color`, `customer_code`, `province_name`,
  `region`, `quantity`, `unit_price`, `line_total`
