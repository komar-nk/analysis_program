"""
Клиент для работы с Google Earth Engine
"""

import os
import sys
import logging
import hashlib
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GEEClient:
    """Клиент для работы с Google Earth Engine"""

    def __init__(self, credentials_path: str = 'credentials.json',
                 cache_dir: str = 'satellite_images',
                 max_cache_size: int = 100):
        """
        Инициализация клиента GEE

        Args:
            credentials_path: Путь к файлу с учетными данными GEE
            cache_dir: Директория для кэширования изображений
            max_cache_size: Максимальное количество изображений в кэше
        """
        # Импортируем обязательные модули
        self._import_required_modules()

        self.credentials_path = credentials_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_cache_size = max_cache_size
        self.request_count = 0
        self._cache_metadata = {}

        # Инициализация GEE
        self._init_gee()

    def _import_required_modules(self):
        """Импорт обязательных модулей"""
        try:
            import ee
            self.ee = ee
        except ImportError:
            print("Модуль 'earthengine-api' не установлен!")
            print("Установите: pip install earthengine-api")
            sys.exit(1)

        try:
            from PIL import Image, ImageEnhance, ImageFilter
            self.Image = Image
            self.ImageEnhance = ImageEnhance
            self.ImageFilter = ImageFilter
        except ImportError:
            print("Модуль 'Pillow' не установлен!")
            print("Установите: pip install pillow")
            sys.exit(1)

        try:
            import cv2
            self.cv2 = cv2
        except ImportError:
            print("Модуль 'opencv-python' не установлен!")
            print("Установите: pip install opencv-python")
            self.cv2 = None

        try:
            import requests
            self.requests = requests
        except ImportError:
            print("Модуль 'requests' не установлен!")
            print("Установите: pip install requests")
            sys.exit(1)

    def _init_gee(self) -> None:
        """Инициализация Google Earth Engine"""
        try:
            print("\n" + "=" * 60)
            print("ИНИЦИАЛИЗАЦИИ GOOGLE EARTH ENGINE")
            print("=" * 60)

            # Твой ID проекта
            PROJECT_ID = "careful-journey-480220-j1"

            print(f"Проект: {PROJECT_ID}")

            # Пробуем инициализацию с использованием credentials.json
            if os.path.exists(self.credentials_path):
                print(f"\nНайден файл {self.credentials_path}")
                print("Инициализируем GEE...")

                try:
                    # Инициализация с проектом
                    self.ee.Initialize(project=PROJECT_ID)
                    print(f"GEE успешно инициализирован!")
                    return
                except self.ee.EEException as e:
                    print(f"Ошибка GEE: {e}")

                    # Если ошибка связана с проектом, пробуем без указания проекта
                    if "project" in str(e).lower():
                        print("Пробуем инициализацию без указания проекта...")
                        try:
                            self.ee.Initialize()
                            print("GEE инициализирован без указания проекта")
                            return
                        except Exception as e2:
                            print(f"Ошибка: {e2}")

                    raise e
            else:
                print(f"\nФайл {self.credentials_path} не найден!")
                print("Создай сервисный аккаунт в Google Cloud Console")
                print("и сохрани credentials.json в папку проекта")

                # Пробуем авторизацию через браузер
                print("\nПробуем авторизацию через браузер...")
                try:
                    self.ee.Authenticate()
                    self.ee.Initialize(project=PROJECT_ID)
                    print("Авторизация через браузер успешна!")
                    return
                except Exception as e:
                    print(f"Ошибка: {e}")

            # Если ничего не сработало
            print("\n" + "=" * 60)
            print("НЕ УДАЛОСЬ ИНИЦИАЛИЗИРОВАТЬ GEE")
            print("=" * 60)

            print("\nЧТО СДЕЛАТЬ:")
            print("1. Перейди: https://code.earthengine.google.com/")
            print("2. Нажми 'Sign Up' или 'Accept' для активации Earth Engine")
            print("3. Обычно это занимает 1-2 дня на одобрение Google")
            print("4. ИЛИ создай сервисный аккаунт в Google Cloud Console")
            print("5. Положи файл credentials.json в папку проекта")

            print("\nПрограмма завершена. Настрой GEE и попробуй снова.")
            sys.exit(0)

        except Exception as e:
            print(f"\nКритическая ошибка инициализации GEE: {e}")
            print("\nРешение:")
            print("1. Проверь интернет-соединение")
            print("2. Убедись что Earth Engine API включен для твоего проекта")
            print("3. Убедись что у сервисного аккаунта есть права Editor/Owner")
            sys.exit(1)

    @staticmethod
    def _get_cache_key(latitude: float, longitude: float, image_date: str) -> str:
        """Генерация ключа кэша для координат и даты"""
        key_str = f"{latitude:.6f}_{longitude:.6f}_{image_date}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached_image(self, latitude: float, longitude: float, image_date: str) -> Optional[str]:
        """Получение изображения из кэша если оно существует"""
        cache_key = self._get_cache_key(latitude, longitude, image_date)
        image_path = self.cache_dir / f"{cache_key}.png"

        if image_path.exists():
            self._cache_metadata[cache_key] = datetime.now()
            logger.debug(f"Изображение найдено в кэше: {image_path}")
            return str(image_path)

        return None

    def _save_to_cache(self, latitude: float, longitude: float, image_date: str, image_path: str) -> None:
        """Сохранение изображения в кэш"""
        try:
            cache_key = self._get_cache_key(latitude, longitude, image_date)

            # Очистка старых файлов если кэш переполнен
            if len(self._cache_metadata) >= self.max_cache_size:
                self._clean_old_cache()

            self._cache_metadata[cache_key] = datetime.now()
            logger.debug(f"Изображение сохранено в кэш: {image_path}")

        except Exception as cache_error:
            logger.error(f"Ошибка при сохранении в кэш: {cache_error}")

    def _clean_old_cache(self) -> None:
        """Очистка старых файлов кэша"""
        try:
            if not self._cache_metadata:
                return

            sorted_items = sorted(self._cache_metadata.items(), key=lambda item: item[1])
            to_remove = max(1, int(len(sorted_items) * 0.2))

            for cache_key, _ in sorted_items[:to_remove]:
                image_path = self.cache_dir / f"{cache_key}.png"
                if image_path.exists():
                    try:
                        image_path.unlink()
                        logger.debug(f"Удален старый файл кэша: {image_path}")
                    except OSError:
                        pass

                if cache_key in self._cache_metadata:
                    del self._cache_metadata[cache_key]

        except Exception as clean_error:
            logger.error(f"Ошибка при очистке кэша: {clean_error}")

    def _enhance_image(self, image_path: str) -> str:
        """Улучшение изображения для лучшей детекции изменений"""
        try:
            # Открываем изображение
            img = self.Image.open(image_path)

            # 1. Увеличиваем яркость (сделает детали видимыми)
            enhancer = self.ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.4)  # +40% яркости

            # 2. Увеличиваем контраст (улучшит границы объектов)
            enhancer = self.ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.4)  # +40% контраста

            # 3. Легкое увеличение резкости (улучшит детали)
            enhancer = self.ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.3)  # +30% резкости

            # 4. Легкое размытие для уменьшения пиксельности
            img = img.filter(self.ImageFilter.GaussianBlur(radius=0.5))

            # 5. Снова легкая резкость для компенсации
            enhancer = self.ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)  # +10% резкости

            # Сохраняем с высоким качеством
            img.save(image_path, 'PNG', optimize=True, quality=95)

            return image_path

        except Exception as e:
            logger.error(f"Ошибка улучшения изображения: {e}")
            return image_path

    def get_satellite_image(self, latitude: float, longitude: float,
                            date: Optional[str] = None,
                            cloud_cover_threshold: float = 30.0,
                            image_size: int = 2048) -> Tuple[bool, Optional[str], Optional[str], str]:
        """
        Получение спутникового изображения с ОПТИМАЛЬНЫМИ НАСТРОЙКАМИ

        Args:
            latitude: Широта
            longitude: Долгота
            date: Дата (YYYY-MM-DD) или None для текущей
            cloud_cover_threshold: Максимальная облачность в %
            image_size: Размер изображения (2048 = оптимально для детекции)

        Returns:
            (успех, путь_к_файлу, дата_изображения, сообщение)
        """
        try:
            # Оптимальный размер для детекции изменений
            if image_size > 2048:
                image_size = 2048  # Максимум без ошибок

            if date is None:
                actual_date = datetime.now().strftime('%Y-%m-%d')
            else:
                actual_date = date

            print(f"\nПоиск изображения для детекции изменений...")
            print(f"Координаты: {latitude:.4f}, {longitude:.4f}")
            print(f"Дата запроса: {actual_date}")
            print(f"Максимальная облачность: {cloud_cover_threshold}%")
            print(f"Размер изображения: {image_size}x{image_size} пикселей")
            print(f"Область: {image_size * 10 / 1000:.1f}x{image_size * 10 / 1000:.1f} км")

            # Проверяем кэш
            cached_image = self._get_cached_image(latitude, longitude, actual_date)
            if cached_image:
                print("Используем изображение из кэша")
                return True, cached_image, actual_date, "Изображение из кэша"

            # Создаем точку интереса
            point = self.ee.Geometry.Point([longitude, latitude])

            # Определяем диапазон дат
            try:
                target_date = datetime.strptime(actual_date, '%Y-%m-%d')
            except ValueError as date_error:
                return False, None, None, f"Некорректный формат даты: {date_error}"

            # Ищем за последние 60 дней
            start_date = (target_date - timedelta(days=60)).strftime('%Y-%m-%d')
            end_date = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')

            print(f"Поиск изображений с {start_date} по {end_date}")

            # Загружаем коллекцию Sentinel-2
            collection = (self.ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                          .filterBounds(point)
                          .filterDate(start_date, end_date)
                          .filter(self.ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover_threshold))
                          .sort('CLOUDY_PIXEL_PERCENTAGE'))

            # Проверяем наличие изображений
            collection_size = collection.size().getInfo()
            print(f"Найдено изображений: {collection_size}")

            if collection_size == 0:
                return False, None, None, f"Нет изображений с облачностью < {cloud_cover_threshold}%"

            # Выбираем наименее облачное изображение
            image = self.ee.Image(collection.first())

            # Получаем дату захвата
            image_date = self.ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()

            # Получаем облачность изображения
            cloud_cover = image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
            print(f"Найдено изображение от: {image_date}")
            print(f"Облачность изображения: {cloud_cover}%")

            # Определяем область интереса (1.5x1.5 км - меньше область, больше деталей!)
            region = point.buffer(750).bounds()  # 750 метров = 1.5x1.5 км

            print("Получаем URL для скачивания...")

            # ОПТИМАЛЬНЫЕ НАСТРОЙКИ ДЛЯ ДЕТЕКЦИИ ИЗМЕНЕНИЙ:
            # Меньшая область + лучшие настройки контраста

            # Генерируем URL для скачивания
            url = image.getThumbURL({
                'region': region,
                'dimensions': f'{image_size}x{image_size}',
                'format': 'png',
                'bands': ['B4', 'B3', 'B2'],  # True Color (RGB)
                'min': 500,  # Увеличил для лучшего контраста
                'max': 3000,  # Оптимально для Sentinel-2
                'gamma': 1.0  # Нейтральная гамма
            })

            print(f"Скачиваем изображение...")

            # Скачиваем изображение
            response = self.requests.get(url, timeout=120)
            if response.status_code != 200:
                return False, None, None, f"Ошибка скачивания: {response.status_code}"

            # Сохраняем изображение
            cache_key = self._get_cache_key(latitude, longitude, image_date)
            filepath = self.cache_dir / f"{cache_key}_{image_size}.png"

            print(f"Сохраняем изображение...")

            # Сохраняем скачанное изображение
            with open(filepath, 'wb') as f:
                f.write(response.content)

            # УЛУЧШАЕМ ИЗОБРАЖЕНИЕ для детекции
            print("Улучшаем изображение для детекции изменений...")
            self._enhance_image(str(filepath))

            # Получаем информацию о размере
            pil_image = self.Image.open(filepath)
            width, height = pil_image.size
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

            # Расчёт детализации
            area_km = (width * 10 / 1000) * (height * 10 / 1000)
            print(f"\nИЗОБРАЖЕНИЕ СОХРАНЕНО!")
            print(f"   Размер: {width}x{height} пикселей")
            print(f"   Область: {area_km:.1f} км²")
            print(f"   Детализация: {10.0 * 1000 / image_size:.1f} метров на пиксель")
            print(f"   Размер файла: {file_size_mb:.2f} MB")
            print(f"   Дата съемки: {image_date}")
            print(f"   Облачность: {cloud_cover}%")
            print(f"   Путь: {filepath}")

            # Сохраняем в кэш
            self._save_to_cache(latitude, longitude, image_date, str(filepath))
            self.request_count += 1

            return True, str(filepath), image_date, f"Успешно ({width}x{height}, {area_km:.1f}км²)"

        except self.ee.EEException as gee_error:
            return False, None, None, f"Ошибка GEE: {str(gee_error)}"
        except Exception as error:
            return False, None, None, f"Внутренняя ошибка: {str(error)}"

    def get_image_for_change_detection(self, latitude: float, longitude: float,
                                       date: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str], str]:
        """
        Специальный метод для получения изображений для детекции изменений
        (меньшая область, лучшие настройки)
        """
        return self.get_satellite_image(
            latitude, longitude, date,
            cloud_cover_threshold=20.0,  # Строже к облачности
            image_size=2048  # Максимальная детализация
        )

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Анализ изображения с помощью OpenCV

        Args:
            image_path: Путь к изображению

        Returns:
            Словарь с результатами анализа
        """
        if self.cv2 is None:
            return {'error': 'OpenCV не установлен. Установите: pip install opencv-python'}

        if not os.path.exists(image_path):
            return {'error': f'Файл не существует: {image_path}'}

        try:
            img = self.cv2.imread(image_path)
            if img is None:
                return {'error': 'Не удалось загрузить изображение'}

            height, width, channels = img.shape

            # Конвертируем в grayscale
            gray = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2GRAY)

            # Статистика яркости
            brightness_mean = gray.mean()
            brightness_std = gray.std()
            min_val, max_val, _, _ = self.cv2.minMaxLoc(gray)

            # Оценка облачности
            _, bright_mask = self.cv2.threshold(gray, 200, 255, self.cv2.THRESH_BINARY)
            cloud_pixels = self.cv2.countNonZero(bright_mask)
            cloud_percentage = (cloud_pixels / (width * height)) * 100

            # Оценка резкости (важно для детекции!)
            edges = self.cv2.Canny(gray, 100, 200)
            edge_pixels = self.cv2.countNonZero(edges)
            edge_percentage = (edge_pixels / (width * height)) * 100

            # Контрастность (важно для детекции!)
            contrast = max_val - min_val

            # Определяем оценку
            cloud_assessment = 'низкая' if cloud_percentage < 10 else 'умеренная' if cloud_percentage < 30 else 'высокая'
            sharpness_assessment = 'низкая' if edge_percentage < 3 else 'средняя' if edge_percentage < 8 else 'высокая'
            contrast_assessment = 'низкий' if contrast < 100 else 'средний' if contrast < 150 else 'высокий'

            return {
                'dimensions': {'width': width, 'height': height},
                'brightness': {
                    'mean': float(brightness_mean),
                    'std': float(brightness_std),
                    'min': float(min_val),
                    'max': float(max_val)
                },
                'contrast': {
                    'value': float(contrast),
                    'assessment': contrast_assessment
                },
                'cloud_cover': {
                    'percentage': float(cloud_percentage),
                    'assessment': cloud_assessment
                },
                'sharpness': {
                    'edge_pixels': int(edge_pixels),
                    'edge_percentage': float(edge_percentage),
                    'assessment': sharpness_assessment
                },
                'suitable_for_change_detection': edge_percentage > 3 and contrast > 80 and cloud_percentage < 40
            }

        except Exception as analysis_error:
            return {'error': f'Ошибка анализа: {str(analysis_error)}'}

    def _detect_seasonal_changes(self, img1, img2):
        """
        Детекция сезонных изменений между двумя изображениями
        """
        try:
            # Конвертируем в grayscale
            gray1 = self.cv2.cvtColor(img1, self.cv2.COLOR_BGR2GRAY)
            gray2 = self.cv2.cvtColor(img2, self.cv2.COLOR_BGR2GRAY)

            # Анализ яркости
            mean_brightness1 = gray1.mean()
            mean_brightness2 = gray2.mean()
            brightness_ratio = max(mean_brightness1, mean_brightness2) / min(mean_brightness1, mean_brightness2)

            # Анализ зеленого канала (растительность)
            green1 = img1[:, :, 1]  # G канал
            green2 = img2[:, :, 1]  # G канал
            mean_green1 = green1.mean()
            mean_green2 = green2.mean()
            green_ratio = mean_green2 / mean_green1 if mean_green1 > 0 else 1

            # Определяем вероятные сезонные изменения
            is_seasonal = False
            seasonal_reason = ""

            # Критерии сезонных изменений
            if brightness_ratio > 1.5:
                is_seasonal = True
                if brightness_ratio > 1.7:
                    seasonal_reason += f"Экстремальная разница в освещении (x{brightness_ratio:.2f}). "
                else:
                    seasonal_reason += f"Значительная разница в освещении (x{brightness_ratio:.2f}). "

            if green_ratio > 1.5 or green_ratio < 0.67:  # Более 50% разницы
                is_seasonal = True
                if green_ratio > 1.5:
                    seasonal_reason += f"Сильное увеличение растительности (x{green_ratio:.2f}). "
                else:
                    seasonal_reason += f"Сильное уменьшение растительности (x{green_ratio:.2f}). "

            # Анализ общего цвета (HSV)
            hsv1 = self.cv2.cvtColor(img1, self.cv2.COLOR_BGR2HSV)
            hsv2 = self.cv2.cvtColor(img2, self.cv2.COLOR_BGR2HSV)

            # Разница в насыщенности (S канал)
            saturation_diff = abs(hsv1[:, :, 1].mean() - hsv2[:, :, 1].mean())
            if saturation_diff > 20:
                is_seasonal = True
                seasonal_reason += f"Разница в насыщенности цвета ({saturation_diff:.1f}%). "

            if not seasonal_reason and is_seasonal:
                seasonal_reason = "Признаки сезонных изменений (освещение, цвет, растительность)"

            return {
                'is_seasonal': is_seasonal,
                'seasonal_reason': seasonal_reason,
                'brightness_ratio': brightness_ratio,
                'green_ratio': green_ratio,
                'mean_brightness1': float(mean_brightness1),
                'mean_brightness2': float(mean_brightness2),
                'mean_green1': float(mean_green1),
                'mean_green2': float(mean_green2)
            }

        except Exception as e:
            print(f"Ошибка детекции сезонных изменений: {e}")
            return {
                'is_seasonal': False,
                'seasonal_reason': 'Ошибка анализа',
                'brightness_ratio': 1.0,
                'green_ratio': 1.0
            }

    def _compare_normal_changes(self, img1, img2, w, h):
        """УЛУЧШЕННОЕ сравнение для НЕ сезонных снимков с фокусом на землю"""
        print("🔍 Улучшенное сравнение (фокус на земляные изменения)...")

        # Функции для препроцессинга
        def preprocess_for_earth(image):
            """Предобработка с акцентом на землю"""
            # 1. Нормализация освещения (CLAHE)
            lab = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2LAB)
            l, a, b = self.cv2.split(lab)
            clahe = self.cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            merged = self.cv2.merge([cl, a, b])
            normalized = self.cv2.cvtColor(merged, self.cv2.COLOR_LAB2BGR)

            # 2. Фокус на цветах земли (коричневые/зеленые тона)
            hsv = self.cv2.cvtColor(normalized, self.cv2.COLOR_BGR2HSV)

            # Маска для цветов земли
            # Коричневые/земляные тона (H: 10-30, S: 30-150, V: 30-150)
            lower_earth1 = np.array([10, 30, 30])
            upper_earth1 = np.array([30, 150, 150])
            mask1 = self.cv2.inRange(hsv, lower_earth1, upper_earth1)

            # Зеленые тона (растительность) - H: 35-85
            lower_earth2 = np.array([35, 30, 30])
            upper_earth2 = np.array([85, 150, 150])
            mask2 = self.cv2.inRange(hsv, lower_earth2, upper_earth2)

            # Красноватые земли - H: 0-10
            lower_earth3 = np.array([0, 30, 30])
            upper_earth3 = np.array([10, 150, 150])
            mask3 = self.cv2.inRange(hsv, lower_earth3, upper_earth3)

            # Объединяем маски земли
            earth_mask = self.cv2.bitwise_or(mask1, mask2)
            earth_mask = self.cv2.bitwise_or(earth_mask, mask3)

            # 3. Убираем облака (высокая яркость во всех каналах)
            gray = self.cv2.cvtColor(normalized, self.cv2.COLOR_BGR2GRAY)
            _, cloud_mask = self.cv2.threshold(gray, 200, 255, self.cv2.THRESH_BINARY)
            cloud_mask_inv = self.cv2.bitwise_not(cloud_mask)

            # 4. Объединяем: оставляем только землю без облаков
            final_mask = self.cv2.bitwise_and(earth_mask, cloud_mask_inv)

            # Применяем маску
            result = self.cv2.bitwise_and(normalized, normalized, mask=final_mask)

            # Заполняем черные области средним цветом земли
            mean_val = self.cv2.mean(normalized, mask=final_mask)[:3]
            result[final_mask == 0] = mean_val

            # 5. Размытие для удаления шума
            result = self.cv2.GaussianBlur(result, (5, 5), 0)

            return result, final_mask

        # Препроцессинг изображений
        print("   Препроцессинг изображений...")
        img1_processed, mask1 = preprocess_for_earth(img1)
        img2_processed, mask2 = preprocess_for_earth(img2)

        # Конвертируем в grayscale
        gray1 = self.cv2.cvtColor(img1_processed, self.cv2.COLOR_BGR2GRAY)
        gray2 = self.cv2.cvtColor(img2_processed, self.cv2.COLOR_BGR2GRAY)

        # Нормализация яркости
        mean1 = gray1.mean()
        mean2 = gray2.mean()

        if abs(mean1 - mean2) > 30:
            alpha = mean1 / mean2 if mean2 > 0 else 1.0
            gray2 = self.cv2.convertScaleAbs(gray2, alpha=alpha, beta=0)

        # Улучшение контраста для детекции земляных изменений
        gray1_eq = self.cv2.equalizeHist(gray1)
        gray2_eq = self.cv2.equalizeHist(gray2)

        # Умеренное размытие (убирает мелкие детали, оставляет крупные изменения)
        gray1_blur = self.cv2.GaussianBlur(gray1_eq, (5, 5), 1.5)
        gray2_blur = self.cv2.GaussianBlur(gray2_eq, (5, 5), 1.5)

        # Вычисляем разницу
        diff = self.cv2.absdiff(gray1_blur, gray2_blur)

        # ПОНИЖЕННЫЙ ПОРОГ для лучшей детекции земляных изменений
        # (вскопанная земля может давать не очень контрастную разницу)
        _, thresh = self.cv2.threshold(diff, 15, 255, self.cv2.THRESH_BINARY)

        # Морфологические операции для объединения близких изменений
        kernel = self.cv2.getStructuringElement(self.cv2.MORPH_ELLIPSE, (5, 5))
        thresh = self.cv2.morphologyEx(thresh, self.cv2.MORPH_CLOSE, kernel)  # Заполнение дыр
        thresh = self.cv2.morphologyEx(thresh, self.cv2.MORPH_OPEN, kernel)  # Удаление шума

        # Применяем маску земли к результату (чтобы не видеть изменения в облаках)
        if mask1 is not None and mask2 is not None:
            # Объединяем маски из обоих изображений
            combined_mask = self.cv2.bitwise_or(mask1, mask2)
            # Оставляем только изменения в областях земли
            thresh = self.cv2.bitwise_and(thresh, combined_mask)

        # Находим контуры
        contours, _ = self.cv2.findContours(thresh, self.cv2.RETR_EXTERNAL,
                                            self.cv2.CHAIN_APPROX_SIMPLE)

        # Фильтруем контуры по площади (ищем только КРУПНЫЕ изменения)
        min_area = (w * h) * 0.0002  # 0.02% от площади (для земляных работ обычно крупные)
        large_mask = np.zeros_like(thresh)
        large_contours = []

        for contour in contours:
            area = self.cv2.contourArea(contour)
            if area > min_area:
                large_contours.append(contour)
                self.cv2.drawContours(large_mask, [contour], -1, 255, -1)

        print(f"   Найдено крупных контуров: {len(large_contours)}")

        # Расчет процента изменений
        changed_pixels = self.cv2.countNonZero(large_mask)
        total_pixels = w * h
        change_percentage = (changed_pixels / total_pixels) * 100

        # Анализ типа изменений
        if large_contours:
            avg_area = sum(self.cv2.contourArea(c) for c in large_contours) / len(large_contours)
            print(f"   Средняя площадь изменений: {avg_area:.0f} пикс.")

            # Если изменения крупные и компактные - похоже на земляные работы
            if avg_area > min_area * 3:
                print("   Вероятно, земляные работы")

        return change_percentage, large_contours, changed_pixels

    def _compare_seasonal_changes(self, img1, img2, w, h, seasonal_data):
        """Сравнение для СЕЗОННЫХ снимков (ищет только структурные изменения)"""
        print("🔍 Сравнение сезонных снимков (только структуры)...")

        # Конвертируем в grayscale
        gray1 = self.cv2.cvtColor(img1, self.cv2.COLOR_BGR2GRAY)
        gray2 = self.cv2.cvtColor(img2, self.cv2.COLOR_BGR2GRAY)

        # Нормализация яркости (компенсация зимнего/летнего освещения)
        if seasonal_data['brightness_ratio'] > 1.2:
            alpha = seasonal_data['mean_brightness1'] / seasonal_data['mean_brightness2']
            gray2 = self.cv2.convertScaleAbs(gray2, alpha=alpha, beta=0)

        # СИЛЬНОЕ размытие (оставляем только крупные структуры)
        gray1_blur = self.cv2.GaussianBlur(gray1, (15, 15), 5.0)
        gray2_blur = self.cv2.GaussianBlur(gray2, (15, 15), 5.0)

        # Высокий порог - только явные структурные изменения
        diff = self.cv2.absdiff(gray1_blur, gray2_blur)
        _, thresh = self.cv2.threshold(diff, 50, 255, self.cv2.THRESH_BINARY)

        # Находим контуры
        contours, _ = self.cv2.findContours(thresh, self.cv2.RETR_EXTERNAL,
                                            self.cv2.CHAIN_APPROX_SIMPLE)

        # Только КРУПНЫЕ контуры (>2% площади)
        min_area = (w * h) * 0.02  # 2% от площади!

        structural_changes = []
        structural_mask = np.zeros_like(thresh)

        for cnt in contours:
            area = self.cv2.contourArea(cnt)
            if area > min_area:
                structural_changes.append(cnt)
                self.cv2.drawContours(structural_mask, [cnt], -1, 255, -1)

        # Расчет процента
        changed_pixels = self.cv2.countNonZero(structural_mask)
        total_pixels = w * h
        change_percentage = (changed_pixels / total_pixels) * 100

        return change_percentage, structural_changes, changed_pixels

    def compare_images_advanced(self, image_path1: str, image_path2: str) -> Dict[str, Any]:
        """
        УЛУЧШЕННОЕ сравнение двух изображений с фильтром сезонности
        """
        if self.cv2 is None:
            return {'error': 'OpenCV не установлен'}

        if not all(os.path.exists(p) for p in [image_path1, image_path2]):
            return {'error': 'Один или оба файла не существуют'}

        try:
            start_time = time.time()

            print(f"\n{'=' * 60}")
            print("🔍 СРАВНЕНИЕ ИЗОБРАЖЕНИЙ С ФИЛЬТРОМ СЕЗОННОСТИ")
            print(f"{'=' * 60}")

            # Загружаем изображения
            img1 = self.cv2.imread(image_path1)
            img2 = self.cv2.imread(image_path2)

            if img1 is None or img2 is None:
                return {'error': 'Не удалось загрузить изображения'}

            # Приводим к одинаковому размеру
            h = min(img1.shape[0], img2.shape[0])
            w = min(img1.shape[1], img2.shape[1])
            img1 = self.cv2.resize(img1, (w, h))
            img2 = self.cv2.resize(img2, (w, h))

            print(f"Размер изображений: {w}x{h} пикселей")

            # ШАГ 1: Проверка сезонности
            print("\n1. Анализ сезонности...")
            seasonal_data = self._detect_seasonal_changes(img1, img2)

            print(f"   Яркость: {seasonal_data['mean_brightness1']:.1f} → {seasonal_data['mean_brightness2']:.1f}")
            print(f"   Растительность: {seasonal_data['mean_green1']:.1f} → {seasonal_data['mean_green2']:.1f}")
            print(f"   Сезонные изменения: {'Да' if seasonal_data['is_seasonal'] else 'Нет'}")

            is_seasonal = seasonal_data['is_seasonal']

            if is_seasonal:
                print(f"   ️  ПРИЧИНА: {seasonal_data['seasonal_reason']}")
                print(f"    Будет использоваться структурный алгоритм")

            # ШАГ 2: Выбор алгоритма сравнения
            if is_seasonal:
                # Для сезонных снимков используем структурный алгоритм
                change_percentage, contours, changed_pixels = self._compare_seasonal_changes(
                    img1, img2, w, h, seasonal_data
                )
                algorithm_type = "структурный (сезонные снимки)"
            else:
                # Для несезонных снимков используем нормальный алгоритм
                change_percentage, contours, changed_pixels = self._compare_normal_changes(
                    img1, img2, w, h
                )
                algorithm_type = "нормальный"

            total_pixels = w * h

            print(f"\n📊 РЕЗУЛЬТАТЫ ({algorithm_type}):")
            print(f"   Контуров найдено: {len(contours)}")
            print(f"   Измененные пиксели: {changed_pixels:,}")
            print(f"   Всего пикселей: {total_pixels:,}")
            print(f"   Процент изменений: {change_percentage:.2f}%")

            # ШАГ 3: Определение уровня изменений
            if is_seasonal:
                # Для сезонных снимков - другие пороги
                if change_percentage < 0.3:
                    change_level = 'отсутствуют'
                    significance = 'Только сезонные изменения'
                elif change_percentage < 1.0:
                    change_level = 'минимальные'
                    significance = 'Минимальные структурные изменения'
                elif change_percentage < 3.0:
                    change_level = 'незначительные'
                    significance = 'Незначительные структурные изменения'
                elif change_percentage < 8.0:
                    change_level = 'умеренные'
                    significance = 'Заметные структурные изменения'
                elif change_percentage < 15.0:
                    change_level = 'значительные'
                    significance = 'Значительные структурные изменения'
                else:
                    change_level = 'критические'
                    significance = 'Критические структурные изменения'
            else:
                # Для несезонных снимков - обычные пороги
                if change_percentage < 0.5:
                    change_level = 'отсутствуют'
                    significance = 'Нет значимых изменений'
                elif change_percentage < 2.0:
                    change_level = 'минимальные'
                    significance = 'Минимальные изменения'
                elif change_percentage < 5.0:
                    change_level = 'умеренные'
                    significance = 'Заметные изменения'
                elif change_percentage < 10.0:
                    change_level = 'значительные'
                    significance = 'Значительные изменения'
                elif change_percentage < 20.0:
                    change_level = 'критические'
                    significance = 'Критические изменения'
                else:
                    change_level = 'катастрофические'
                    significance = 'Катастрофические изменения'

            # ШАГ 4: Визуализация
            timestamp = int(time.time())
            visualization_path = f"changes_visualization_{timestamp}.jpg"

            # Создаем визуализацию
            result_img = img2.copy()

            # Рисуем контуры изменений красным
            self.cv2.drawContours(result_img, contours, -1, (0, 0, 255), 2)

            # Полупрозрачная заливка
            overlay = result_img.copy()
            for cnt in contours:
                self.cv2.drawContours(overlay, [cnt], -1, (0, 0, 255), -1)

            self.cv2.addWeighted(overlay, 0.3, result_img, 0.7, 0, result_img)

            # Добавляем текст
            font = self.cv2.FONT_HERSHEY_SIMPLEX
            text = f"Changes: {change_percentage:.2f}% ({change_level})"
            if is_seasonal:
                text += " [Сезонные]"

            self.cv2.putText(result_img, text, (10, 30), font, 1, (0, 0, 255), 2)

            # Сохраняем
            self.cv2.imwrite(visualization_path, result_img)
            print(f"📸 Визуализация сохранена: {visualization_path}")

            elapsed_time = time.time() - start_time

            print(f"\n{'=' * 60}")
            print("✅ ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:")
            print(f"{'=' * 60}")
            print(f"Изменения: {change_percentage:.4f}% ({change_level})")
            print(f"Сезонные: {'Да' if is_seasonal else 'Нет'}")
            if is_seasonal:
                print(f"Причина: {seasonal_data['seasonal_reason']}")
            print(f"Время обработки: {elapsed_time:.1f} сек")
            print(f"{'=' * 60}")

            # Возвращаем данные
            return {
                'changed_pixels': int(changed_pixels),
                'total_pixels': int(total_pixels),
                'change_percentage': float(change_percentage),
                'change_level': change_level,
                'significance': significance,
                'contours_count': len(contours),
                'is_seasonal': is_seasonal,
                'seasonal_reason': seasonal_data['seasonal_reason'] if is_seasonal else '',
                'brightness_ratio': float(seasonal_data['brightness_ratio']),
                'green_ratio': float(seasonal_data['green_ratio']),
                'processing_time_seconds': float(elapsed_time),
                'visualization_path': visualization_path,
                'image_dimensions': {'width': w, 'height': h}
            }

        except Exception as comparison_error:
            print(f" Ошибка сравнения: {str(comparison_error)}")
            import traceback
            traceback.print_exc()
            return {'error': f'Ошибка сравнения: {str(comparison_error)}'}

    def compare_images(self, image_path1: str, image_path2: str) -> Dict[str, Any]:
        """Алиас для обратной совместимости"""
        return self.compare_images_advanced(image_path1, image_path2)

    def clear_cache(self) -> str:
        """Очистка кэша изображений"""
        try:
            deleted_count = 0

            for file in self.cache_dir.glob("*.png"):
                try:
                    file.unlink()
                    deleted_count += 1
                except OSError:
                    pass

            self._cache_metadata.clear()

            return f"Очищено {deleted_count} файлов из кэша"

        except Exception as error:
            return f"Ошибка очистки: {error}"

    def get_cache_info(self) -> Dict[str, Any]:
        """Получение информации о кэше"""
        try:
            cache_files = list(self.cache_dir.glob("*.png"))
            total_size = sum(f.stat().st_size for f in cache_files if f.exists())

            return {
                'image_count': len(cache_files),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'request_count': self.request_count,
                'cache_in_memory': len(self._cache_metadata)
            }

        except Exception as error:
            return {'error': str(error)}

    def debug_seasonal_analysis(self, image_path1: str, image_path2: str):
        """Отладка сезонного анализа"""
        print(f"\n{'=' * 60}")
        print("🔬 ОТЛАДКА СЕЗОННОГО АНАЛИЗА")
        print(f"{'=' * 60}")

        img1 = self.cv2.imread(image_path1)
        img2 = self.cv2.imread(image_path2)

        if img1 is None or img2 is None:
            print("Ошибка загрузки изображений")
            return

        # Анализ цвета
        hsv1 = self.cv2.cvtColor(img1, self.cv2.COLOR_BGR2HSV)
        hsv2 = self.cv2.cvtColor(img2, self.cv2.COLOR_BGR2HSV)

        print(f"\nЦВЕТОВОЙ АНАЛИЗ:")
        print(
            f"  Изображение 1 - H: {hsv1[:, :, 0].mean():.1f}, S: {hsv1[:, :, 1].mean():.1f}, V: {hsv1[:, :, 2].mean():.1f}")
        print(
            f"  Изображение 2 - H: {hsv2[:, :, 0].mean():.1f}, S: {hsv2[:, :, 1].mean():.1f}, V: {hsv2[:, :, 2].mean():.1f}")

        # Анализ каналов
        print(f"\nКАНАЛЫ RGB:")
        print(f"  Изобр1 - R: {img1[:, :, 2].mean():.1f}, G: {img1[:, :, 1].mean():.1f}, B: {img1[:, :, 0].mean():.1f}")
        print(f"  Изобр2 - R: {img2[:, :, 2].mean():.1f}, G: {img2[:, :, 1].mean():.1f}, B: {img2[:, :, 0].mean():.1f}")

        # Яркость
        gray1 = self.cv2.cvtColor(img1, self.cv2.COLOR_BGR2GRAY)
        gray2 = self.cv2.cvtColor(img2, self.cv2.COLOR_BGR2GRAY)
        print(f"\nЯРКОСТЬ: {gray1.mean():.1f} → {gray2.mean():.1f} (разница: {abs(gray1.mean() - gray2.mean()):.1f})")

        # Зеленый канал (растительность)
        green_ratio = img2[:, :, 1].mean() / img1[:, :, 1].mean() if img1[:, :, 1].mean() > 0 else 1
        print(f"РАСТИТЕЛЬНОСТЬ (G канал): x{green_ratio:.2f}")

        # Определение сезона
        month_ranges = {
            'зима': (0, 60, 200, 255),  # синий/белый
            'весна': (40, 100, 100, 200),  # зеленый/коричневый
            'лето': (50, 120, 150, 250),  # ярко-зеленый
            'осень': (20, 60, 100, 180)  # желтый/оранжевый
        }

        print(f"\nВЕРОЯТНЫЙ СЕЗОН:")
        for season, (h_min, h_max, s_min, s_max) in month_ranges.items():
            mask1 = cv2.inRange(hsv1, (h_min, s_min, 50), (h_max, s_max, 255))
            mask2 = cv2.inRange(hsv2, (h_min, s_min, 50), (h_max, s_max, 255))

            percent1 = (cv2.countNonZero(mask1) / (img1.shape[0] * img1.shape[1])) * 100
            percent2 = (cv2.countNonZero(mask2) / (img2.shape[0] * img2.shape[1])) * 100

            print(f"  {season}: {percent1:.1f}% → {percent2:.1f}%")

        seasonal_data = self._detect_seasonal_changes(img1, img2)
        print(f"\nИТОГ: Сезонные изменения - {'Да' if seasonal_data['is_seasonal'] else 'Нет'}")


# Тестовый запуск
if __name__ == "__main__":
    print("Тестирование GEE клиента с фильтром сезонности...")
    print(f"Проект: careful-journey-480220-j1")

    try:
        client = GEEClient()
        print("\n✅ Клиент создан успешно!")

        print("\nТест 1: Проверка сезонного анализа...")
        # Тестовые изображения
        test_image1 = "test_winter.jpg"  # зимний снимок
        test_image2 = "test_summer.jpg"  # летний снимок

        # Если тестовых файлов нет, создаем
        if not os.path.exists(test_image1) or not os.path.exists(test_image2):
            print("Создаю тестовые изображения...")
            import numpy as np

            # Зимнее изображение (снег, голые деревья)
            winter_img = np.zeros((300, 400, 3), dtype=np.uint8)
            winter_img[:, :] = [200, 220, 240]  # сине-белый
            cv2.rectangle(winter_img, (100, 100), (200, 200), [150, 150, 150], -1)  # здание

            # Летнее изображение (трава, зелень)
            summer_img = np.zeros((300, 400, 3), dtype=np.uint8)
            summer_img[:, :] = [50, 150, 50]  # зеленый
            cv2.rectangle(summer_img, (100, 100), (200, 200), [150, 150, 150], -1)  # то же здание

            cv2.imwrite(test_image1, winter_img)
            cv2.imwrite(test_image2, summer_img)
            print(f"Тестовые изображения созданы: {test_image1}, {test_image2}")

        # Анализ сезонности
        client.debug_seasonal_analysis(test_image1, test_image2)

        # Сравнение
        result = client.compare_images_advanced(test_image1, test_image2)

        if 'error' not in result:
            print(f"\n📊 РЕЗУЛЬТАТ СРАВНЕНИЯ:")
            print(f"   Изменения: {result['change_percentage']:.2f}%")
            print(f"   Уровень: {result['change_level']}")
            print(f"   Сезонные: {'Да' if result['is_seasonal'] else 'Нет'}")
            print(f"   Контуров: {result['contours_count']}")

            if result['is_seasonal']:
                print(f"    ВЕРНО: Обнаружены сезонные изменения")
                print(f"    Структурные изменения: {result['change_percentage']:.2f}% (должно быть мало)")
            else:
                print(f"    ОШИБКА: Не обнаружены сезонные изменения (должны быть!)")

        # Очистка тестовых файлов
        if os.path.exists(test_image1):
            os.remove(test_image1)
        if os.path.exists(test_image2):
            os.remove(test_image2)

    except Exception as e:
        print(f" Ошибка: {e}")
        import traceback

        traceback.print_exc()