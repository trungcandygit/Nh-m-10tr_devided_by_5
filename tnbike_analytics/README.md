# tnbike_analytics — Developer Guide

→ Tài liệu đầy đủ: [README.md](../README.md) | Data dictionary: [DATA_DICTIONARY.md](../DATA_DICTIONARY.md)

---

## Cài đặt

```bash
pip install -r dashboard/requirements.txt
```

## Chạy

```bash
# Sinh toàn bộ CSV
python export_csv.py

# Tests (tự sinh output/test_report.md)
pytest tests/ -v

# Dashboard
cd dashboard && python index.py   # http://localhost:8050

# Pipeline email → DB (cần PostgreSQL + file .eml/.pdf)
cp .env.example .env              # điền thông tin DB
python -m pipeline.run_pipeline --email-dir data/raw/emails --pdf-dir data/raw/pdfs
```

## Cấu trúc code

| File | Vai trò |
|---|---|
| `export_csv.py` | Entry point — gọi sql_data_loader + prediction_engine → sinh CSV |
| `analytics/sql_data_loader.py` | Parse `02_import_data.sql` → dict DataFrames, không cần DB |
| `analytics/t3_loader.py` | Parse .eml + .pdf T3/2026 → DataFrame ghép vào fact |
| `analytics/prediction_engine.py` | `run_q1_forecast()`, `run_q2_color_demand()`, `run_q3_dealer_forecast()` |
| `dashboard/data_loader.py` | Đọc CSV vào dict cho Dash pages |

## Lưu ý

- `product_code` phải đọc là **string**: `pd.read_csv(..., dtype={"product_code": str})`
- Feature ML chỉ được dùng data ≤ 2025-03-31 (tránh leakage vào label 2026)
- Test leakage tự động: `test_q3_no_leakage_auc_ceiling` bắt lỗi nếu AUC ≥ 0.99
