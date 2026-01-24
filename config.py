"""
Конфигурация системы мониторинга
"""

from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Пути
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "satellite_images"
RESULTS_DIR = BASE_DIR / "changes_results"
CACHE_DIR.mkdir(exist_ok=True)

# Настройки GEE
GEE_CREDENTIALS = BASE_DIR / "credentials.json"

# Параметры изображений
IMAGE_SIZE = 512  # размер изображения в пикселях
CLOUD_COVER_THRESHOLD = 20.0  # максимальная облачность в %
CACHE_MAX_SIZE = 100  # максимальное количество изображений в кэше

# Интервал мониторинга (в часах)
MONITORING_INTERVAL = 24

# Координаты по умолчанию (Москва)
DEFAULT_LOCATION = {
    "name": "Москва, Кремль",
    "lat": 55.7520,
    "lon": 37.6175,
    "description": "Московский Кремль"
}