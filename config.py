"""
Конфигурация системы мониторинга
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "satellite_images"
RESULTS_DIR = BASE_DIR / "changes_results"
CACHE_DIR.mkdir(exist_ok=True)

GEE_CREDENTIALS = BASE_DIR / "credentials.json"

IMAGE_SIZE = 512
CLOUD_COVER_THRESHOLD = 20.0
CACHE_MAX_SIZE = 100

MONITORING_INTERVAL = 24

DEFAULT_LOCATION = {
    "name": "Москва, Кремль",
    "lat": 55.7520,
    "lon": 37.6175,
    "description": "Московский Кремль"
}