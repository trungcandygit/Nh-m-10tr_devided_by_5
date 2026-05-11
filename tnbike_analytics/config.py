"""
Cấu hình toàn dự án tnbike_analytics
Đọc biến môi trường từ .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).parent

DB_HOST     = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT     = int(os.getenv("POSTGRES_PORT", 5432))
DB_NAME     = os.getenv("POSTGRES_DB", "tnbike_db")
DB_USER     = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
DB_SCHEMA   = os.getenv("POSTGRES_SCHEMA", "tnbike")
DB_URL      = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

EMAIL_DIR = Path(os.getenv("EMAIL_DIR", ROOT / "data/raw/emails"))
PDF_DIR   = Path(os.getenv("PDF_DIR",   ROOT / "data/raw/pdfs"))
PROCESSED = Path(os.getenv("PROCESSED_DIR", ROOT / "data/processed"))

ANALYSIS_START   = "2025-01-01"
ANALYSIS_END     = "2026-03-31"
MARCH_2026_START = "2026-03-01"
MARCH_2026_END   = "2026-03-31"
FORECAST_START   = "2026-04-01"
FORECAST_END     = "2026-06-30"

PRODUCT_GROUPS = {
    "CITYBIKE_P":  "Xe phổ thông",
    "KIDBIKE_1":   "Xe trẻ em nhóm 1",
    "KIDBIKE_2":   "Xe trẻ em nhóm 2",
    "SPORTBIKE_S": "Xe thể thao thép",
    "SPORTBIKE_A": "Xe thể thao nhôm",
}

MAIN_COLORS = ["Đen", "Cam", "Xanh mint", "Café/nâu", "Trắng", "Đỏ", "Xanh dương"]
REGIONS     = ["Miền Bắc", "Miền Trung", "Miền Nam"]

RFM_RECENT_DAYS  = 90
RFM_HIGH_FREQ    = 8
RFM_HIGH_VALUE   = 50_000_000

CHURN_INACTIVE_DAYS = 90
