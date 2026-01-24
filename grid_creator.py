"""
Создатель сеток для уведомлений
"""

import cv2
import numpy as np
import os
from typing import Dict, Any, Tuple
from datetime import datetime


class GridCreator:
    def __init__(self, grid_size: int = 32):
        self.grid_size = grid_size

    def create_grid_for_email(self, image_path: str,
                              lat: float, lon: float,
                              territory_name: str = "") -> Dict[str, Any]:
        """
        Создает фотку с сеткой для email уведомления
        """
        print(f"📐 Создание сетки для {territory_name}...")

        # Загружаем изображение
        if not os.path.exists(image_path):
            return {'error': f'Файл не найден: {image_path}'}

        img = cv2.imread(image_path)
        if img is None:
            return {'error': 'Не удалось загрузить изображение'}

        h, w = img.shape[:2]

        # Создаем изображение с сеткой
        grid_img = img.copy()

        # 1. Рисуем сетку
        for i in range(0, h, self.grid_size):
            cv2.line(grid_img, (0, i), (w, i), (0, 255, 255), 1)  # Желтые линии
        for j in range(0, w, self.grid_size):
            cv2.line(grid_img, (j, 0), (j, h), (0, 255, 255), 1)

        # 2. Добавляем координаты по краям (каждые 4 линии)
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Широта слева
        for i in range(0, h, self.grid_size * 4):
            if i < h - 20:
                lat_offset = (i / h) * 0.02  # Примерный расчет
                current_lat = lat + lat_offset
                text = f"{current_lat:.5f}°"
                cv2.putText(grid_img, text, (5, i + 15), font, 0.4, (255, 255, 0), 1)

        # Долгота сверху
        for j in range(0, w, self.grid_size * 4):
            if j < w - 60:
                lon_offset = (j / w) * 0.02
                current_lon = lon + lon_offset
                text = f"{current_lon:.5f}°"
                cv2.putText(grid_img, text, (j + 5, 20), font, 0.4, (255, 255, 0), 1)

        # 3. Информационная панель сверху
        panel_height = 80
        panel = np.zeros((panel_height, w, 3), dtype=np.uint8)
        panel[:] = (40, 40, 60)  # Темно-синий фон

        # Текст на панели
        title = f"КООРДИНАТНАЯ СЕТКА: {territory_name}"
        cv2.putText(panel, title, (10, 25), font, 0.8, (255, 255, 255), 2)

        coord_text = f"Центр: {lat:.5f}°, {lon:.5f}°"
        cv2.putText(panel, coord_text, (10, 50), font, 0.6, (200, 200, 255), 1)

        grid_text = f"Сетка: {self.grid_size}px | Ячеек: {w // self.grid_size}×{h // self.grid_size}"
        cv2.putText(panel, grid_text, (10, 70), font, 0.5, (200, 255, 200), 1)

        # Объединяем панель и изображение
        final_img = np.vstack([panel, grid_img])

        # 4. Легенда снизу
        legend_height = 60
        legend = np.zeros((legend_height, w, 3), dtype=np.uint8)
        legend[:] = (60, 60, 80)

        # Текст легенды
        cv2.putText(legend, "🎯 ЖЕЛТЫЕ ЛИНИИ - координатная сетка", (10, 20),
                    font, 0.5, (255, 255, 0), 1)
        cv2.putText(legend, "📏 РАЗМЕР ЯЧЕЙКИ - 32 пикселя", (10, 40),
                    font, 0.5, (200, 200, 255), 1)

        # Объединяем все
        final_img = np.vstack([final_img, legend])

        # 5. Сохраняем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"grid_{territory_name}_{timestamp}.jpg"
        cv2.imwrite(filename, final_img)

        print(f"✅ Сетка создана: {filename}")

        return {
            'success': True,
            'grid_path': filename,
            'image_size': (w, h),
            'grid_cells': (w // self.grid_size, h // self.grid_size),
            'coordinates': {'lat': lat, 'lon': lon}
        }

    def create_comparison_grid(self, before_path: str, after_path: str,
                               territory_name: str = "") -> Dict[str, Any]:
        """
        Создает сравнение двух изображений с сеткой
        """
        print(f"🔄 Создание сравнительной сетки...")

        if not os.path.exists(before_path) or not os.path.exists(after_path):
            return {'error': 'Файлы не найдены'}

        before = cv2.imread(before_path)
        after = cv2.imread(after_path)

        if before is None or after is None:
            return {'error': 'Ошибка загрузки'}

        # Приводим к одному размеру
        h = min(before.shape[0], after.shape[0])
        w = min(before.shape[1], after.shape[1])

        before = cv2.resize(before, (w, h))
        after = cv2.resize(after, (w, h))

        # Создаем комбинированное изображение
        comparison = np.zeros((h + 100, w * 2, 3), dtype=np.uint8)  # +100 для заголовка
        comparison.fill(40)  # Серый фон

        # Заголовок
        font = cv2.FONT_HERSHEY_SIMPLEX
        title = f"СРАВНЕНИЕ С СЕТКОЙ: {territory_name}"
        cv2.putText(comparison, title, (10, 30), font, 0.8, (255, 255, 255), 2)

        # Вставляем изображения
        comparison[100:100 + h, :w] = before
        comparison[100:100 + h, w:] = after

        # Рисуем сетку на ОБОИХ изображениях
        for i in range(0, h, self.grid_size):
            cv2.line(comparison, (0, 100 + i), (w * 2, 100 + i), (0, 255, 255), 1)
        for j in range(0, w, self.grid_size):
            cv2.line(comparison, (j, 100), (j, 100 + h), (0, 255, 255), 1)
            cv2.line(comparison, (w + j, 100), (w + j, 100 + h), (0, 255, 255), 1)

        # Подписи
        cv2.putText(comparison, "СТАРЫЙ СНИМОК", (10, 80), font, 0.7, (255, 200, 200), 2)
        cv2.putText(comparison, "НОВЫЙ СНИМОК", (w + 10, 80), font, 0.7, (200, 255, 200), 2)

        # Разделительная линия
        cv2.line(comparison, (w, 100), (w, 100 + h), (255, 255, 255), 3)

        # Легенда снизу
        legend_y = 100 + h + 10
        cv2.putText(comparison, "🎯 Сетка 32px для точного определения координат",
                    (10, legend_y), font, 0.5, (255, 255, 0), 1)

        # Сохраняем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comparison_grid_{territory_name}_{timestamp}.jpg"
        cv2.imwrite(filename, comparison)

        print(f"✅ Сравнительная сетка создана: {filename}")

        return {
            'success': True,
            'comparison_path': filename,
            'image_size': (w, h),
            'grid_info': {
                'size': self.grid_size,
                'cells_x': w // self.grid_size,
                'cells_y': h // self.grid_size
            }
        }

    def create_grid_with_changes(self, image_path: str,
                                 changes_mask_path: str,
                                 territory_name: str = "") -> Dict[str, Any]:
        """
        Создает сетку с выделенными изменениями
        """
        print(f"🎨 Создание сетки с изменениями...")

        if not os.path.exists(image_path):
            return {'error': f'Изображение не найдено: {image_path}'}

        img = cv2.imread(image_path)
        if img is None:
            return {'error': 'Ошибка загрузки изображения'}

        h, w = img.shape[:2]

        # Создаем основное изображение
        result = img.copy()

        # Если есть маска изменений - накладываем
        if os.path.exists(changes_mask_path):
            mask = cv2.imread(changes_mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is not None:
                mask = cv2.resize(mask, (w, h))

                # Находим контуры изменений
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Рисуем контуры красным
                cv2.drawContours(result, contours, -1, (0, 0, 255), 2)

                # Полупрозрачная заливка
                overlay = result.copy()
                cv2.drawContours(overlay, contours, -1, (0, 0, 255), -1)
                cv2.addWeighted(overlay, 0.3, result, 0.7, 0, result)

        # Рисуем сетку
        for i in range(0, h, self.grid_size):
            cv2.line(result, (0, i), (w, i), (0, 255, 255), 1)
        for j in range(0, w, self.grid_size):
            cv2.line(result, (j, 0), (j, h), (0, 255, 255), 1)

        # Добавляем заголовок
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Верхняя панель
        panel = np.zeros((60, w, 3), dtype=np.uint8)
        panel[:] = (40, 40, 80)

        title = f"АНАЛИЗ ИЗМЕНЕНИЙ: {territory_name}"
        cv2.putText(panel, title, (10, 25), font, 0.8, (255, 255, 255), 2)

        if os.path.exists(changes_mask_path):
            cv2.putText(panel, "🔴 КРАСНЫЙ - обнаруженные изменения", (10, 50),
                        font, 0.5, (255, 255, 0), 1)
        else:
            cv2.putText(panel, "📐 СЕТКА - координатная разметка", (10, 50),
                        font, 0.5, (255, 255, 0), 1)

        # Объединяем
        final = np.vstack([panel, result])

        # Сохраняем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"changes_grid_{territory_name}_{timestamp}.jpg"
        cv2.imwrite(filename, final)

        print(f"✅ Сетка с изменениями создана: {filename}")

        return {
            'success': True,
            'changes_grid_path': filename,
            'has_changes': os.path.exists(changes_mask_path),
            'contours_count': len(contours) if 'contours' in locals() else 0
        }


# Простые функции для быстрого использования
def create_simple_grid(image_path: str, output_name: str = None) -> str:
    """Быстро создать сетку для одного изображения"""
    creator = GridCreator(grid_size=32)

    if output_name is None:
        output_name = f"grid_{os.path.basename(image_path)}"

    result = creator.create_grid_for_email(
        image_path=image_path,
        lat=55.7558,  # Примерные координаты Москвы
        lon=37.6173,
        territory_name=os.path.basename(image_path)
    )

    return result.get('grid_path', '') if result.get('success') else ''


# Тестирование
if __name__ == "__main__":
    print("🔧 ТЕСТИРОВАНИЕ СОЗДАНИЯ СЕТОК")

    # Тестовые файлы
    test_image = "test_image.jpg"

    if not os.path.exists(test_image):
        print(f"Создаю тестовое изображение: {test_image}")
        # Создаем простое тестовое изображение
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        img[:, :] = [100, 150, 100]  # Зеленый фон

        # Добавляем объекты
        cv2.rectangle(img, (100, 100), (200, 200), [0, 200, 0], -1)  # Зеленый квадрат
        cv2.circle(img, (400, 200), 50, [200, 100, 0], -1)  # Оранжевый круг

        cv2.imwrite(test_image, img)
        print(f"✅ Создано: {test_image}")

    # Тестируем создание сетки
    creator = GridCreator()

    print("\n1. Создание простой сетки...")
    result1 = creator.create_grid_for_email(
        image_path=test_image,
        lat=55.7558,
        lon=37.6173,
        territory_name="Тестовая территория"
    )

    if result1.get('success'):
        print(f"✅ Готово: {result1['grid_path']}")

    print("\n2. Создание сравнительной сетки...")
    # Создаем второе тестовое изображение
    test_image2 = "test_image2.jpg"
    if not os.path.exists(test_image2):
        img2 = cv2.imread(test_image)
        # Меняем немного
        cv2.rectangle(img2, (100, 100), (200, 200), [139, 69, 19], -1)  # Коричневый квадрат
        cv2.imwrite(test_image2, img2)

    result2 = creator.create_comparison_grid(
        before_path=test_image,
        after_path=test_image2,
        territory_name="Тест сравнения"
    )

    if result2.get('success'):
        print(f"✅ Готово: {result2['comparison_path']}")

    print("\n🎯 Все сетки созданы! Можно использовать в уведомлениях.")