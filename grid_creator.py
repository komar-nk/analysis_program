
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
        print(f"Creating grid for {territory_name}...")

        # Функция транслитерации (улучшена для английских имен)
        def transliterate(text: str) -> str:
            if not text:
                return "territory"

            # Сначала попробуем перевести русские буквы
            translit_dict = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
                'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
                'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
                'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
                'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
                'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
                'э': 'e', 'ю': 'yu', 'я': 'ya',
                'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
                'Е': 'E', 'Ё': 'E', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
                'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
                'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
                'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
                'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
                'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
                ' ': '_', '-': '_', ',': '', '.': '', '!': '', '?': '',
                ':': '', ';': '', '(': '', ')': '', '[': '', ']': '',
                '{': '', '}': '', '<': '', '>': '', '/': '', '\\': '',
                '|': '', '"': '', "'": '', '`': '', '~': '', '@': '',
                '#': '', '$': '', '%': '', '^': '', '&': '', '*': '',
                '+': '', '=': ''
            }

            result = []
            for char in text:
                if char in translit_dict:
                    result.append(translit_dict[char])
                elif char.isalnum():
                    result.append(char)
                else:
                    result.append('_')

            result_text = ''.join(result)

            while '__' in result_text:
                result_text = result_text.replace('__', '_')

            result_text = result_text.strip('_')

            if not result_text:
                return "territory"

            if len(result_text) > 50:
                result_text = result_text[:50]

            return result_text.lower()

        # Загружаем изображение
        if not os.path.exists(image_path):
            return {'error': f'File not found: {image_path}'}

        img = cv2.imread(image_path)
        if img is None:
            return {'error': 'Failed to load image'}

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
                lat_offset = (i / h) * 0.02
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

        # 3. Информационная панель сверху (на английском)
        panel_height = 80
        panel = np.zeros((panel_height, w, 3), dtype=np.uint8)
        panel[:] = (40, 40, 60)  # Темно-синий фон

        # Транслитерируем название для отображения
        safe_display_name = transliterate(territory_name)

        # Текст на панели (английский)
        title = f"COORDINATE GRID: {safe_display_name}"
        cv2.putText(panel, title, (10, 25), font, 0.8, (255, 255, 255), 2)

        coord_text = f"Center: {lat:.5f}°, {lon:.5f}°"
        cv2.putText(panel, coord_text, (10, 50), font, 0.6, (200, 200, 255), 1)

        grid_text = f"Grid: {self.grid_size}px | Cells: {w // self.grid_size}×{h // self.grid_size}"
        cv2.putText(panel, grid_text, (10, 70), font, 0.5, (200, 255, 200), 1)

        # Объединяем панель и изображение
        final_img = np.vstack([panel, grid_img])

        # 4. Легенда снизу (английский)
        legend_height = 60
        legend = np.zeros((legend_height, w, 3), dtype=np.uint8)
        legend[:] = (60, 60, 80)

        # Текст легенды
        cv2.putText(legend, "YELLOW LINES - coordinate grid", (10, 20),
                    font, 0.5, (255, 255, 0), 1)
        cv2.putText(legend, "CELL SIZE - 32 pixels", (10, 40),
                    font, 0.5, (200, 200, 255), 1)

        # Объединяем все
        final_img = np.vstack([final_img, legend])

        # 5. Сохраняем с транслитерированным именем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = transliterate(territory_name)
        filename = f"grid_{safe_name}_{timestamp}.jpg"

        cv2.imwrite(filename, final_img)

        print(f"Grid created: {filename}")

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
        print(f"Creating comparison grid...")

        # Функция транслитерации русских букв в латиницу
        def transliterate(text: str) -> str:
            if not text:
                return "territory"

            translit_dict = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
                'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
                'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
                'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
                'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
                'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
                'э': 'e', 'ю': 'yu', 'я': 'ya',
                'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
                'Е': 'E', 'Ё': 'E', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
                'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
                'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
                'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
                'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
                'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
                ' ': '_', '-': '_', ',': '', '.': '', '!': '', '?': '',
                ':': '', ';': '', '(': '', ')': '', '[': '', ']': '',
                '{': '', '}': '', '<': '', '>': '', '/': '', '\\': '',
                '|': '', '"': '', "'": '', '`': '', '~': '', '@': '',
                '#': '', '$': '', '%': '', '^': '', '&': '', '*': '',
                '+': '', '=': ''
            }

            result = []
            for char in text:
                if char in translit_dict:
                    result.append(translit_dict[char])
                elif char.isalnum():
                    result.append(char)
                else:
                    result.append('_')

            # Объединяем и чистим
            result_text = ''.join(result)

            # Убираем множественные подчеркивания
            while '__' in result_text:
                result_text = result_text.replace('__', '_')

            # Убираем подчеркивания в начале и конце
            result_text = result_text.strip('_')

            # Если после очистки строка пустая, возвращаем дефолтное значение
            if not result_text:
                return "territory"

            # Ограничиваем длину (максимум 50 символов)
            if len(result_text) > 50:
                result_text = result_text[:50]

            return result_text.lower()  # Все в нижний регистр

        if not os.path.exists(before_path) or not os.path.exists(after_path):
            return {'error': 'Files not found'}

        before = cv2.imread(before_path)
        after = cv2.imread(after_path)

        if before is None or after is None:
            return {'error': 'Loading error'}

        # Приводим к одному размеру
        h = min(before.shape[0], after.shape[0])
        w = min(before.shape[1], after.shape[1])

        before = cv2.resize(before, (w, h))
        after = cv2.resize(after, (w, h))

        # Создаем комбинированное изображение
        comparison = np.zeros((h + 100, w * 2, 3), dtype=np.uint8)  # +100 для заголовка
        comparison.fill(40)  # Серый фон

        # Заголовок (английский)
        font = cv2.FONT_HERSHEY_SIMPLEX
        safe_name = transliterate(territory_name)
        title = f"COMPARISON WITH GRID: {safe_name}"
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

        # Подписи (английский)
        cv2.putText(comparison, "BEFORE", (10, 80), font, 0.7, (255, 200, 200), 2)
        cv2.putText(comparison, "AFTER", (w + 10, 80), font, 0.7, (200, 255, 200), 2)

        # Разделительная линия
        cv2.line(comparison, (w, 100), (w, 100 + h), (255, 255, 255), 3)

        # Легенда снизу (английский)
        legend_y = 100 + h + 10
        cv2.putText(comparison, "Grid 32px for precise coordinate determination",
                    (10, legend_y), font, 0.5, (255, 255, 0), 1)

        # Сохраняем с транслитерированным именем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Транслитерируем название территории
        safe_name = transliterate(territory_name)
        filename = f"comparison_grid_{safe_name}_{timestamp}.jpg"

        # Сохраняем в текущую директорию
        cv2.imwrite(filename, comparison, [cv2.IMWRITE_JPEG_QUALITY, 90])

        print(f"Comparison grid created: {filename}")

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
        print(f"Creating grid with changes...")

        if not os.path.exists(image_path):
            return {'error': f'Image not found: {image_path}'}

        img = cv2.imread(image_path)
        if img is None:
            return {'error': 'Image loading error'}

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

        # Верхняя панель (английский)
        panel = np.zeros((60, w, 3), dtype=np.uint8)
        panel[:] = (40, 40, 80)

        # Транслитерируем название
        def transliterate_simple(text: str) -> str:
            if not text:
                return "territory"
            # Простая транслитерация
            return ''.join(c if c.isalnum() else '_' for c in text).lower().replace('__', '_')[:30]

        safe_name = transliterate_simple(territory_name)
        title = f"CHANGES ANALYSIS: {safe_name}"
        cv2.putText(panel, title, (10, 25), font, 0.8, (255, 255, 255), 2)

        if os.path.exists(changes_mask_path):
            cv2.putText(panel, "RED - detected changes", (10, 50),
                        font, 0.5, (255, 255, 0), 1)
        else:
            cv2.putText(panel, "GRID - coordinate grid", (10, 50),
                        font, 0.5, (255, 255, 0), 1)

        # Объединяем
        final = np.vstack([panel, result])

        # Сохраняем с английским именем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = transliterate_simple(territory_name)
        filename = f"changes_grid_{safe_filename}_{timestamp}.jpg"
        cv2.imwrite(filename, final)

        print(f"Grid with changes created: {filename}")

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
        base_name = os.path.basename(image_path).split('.')[0]
        safe_name = ''.join(c if c.isalnum() else '_' for c in base_name).lower()
        output_name = f"grid_{safe_name}.jpg"

    result = creator.create_grid_for_email(
        image_path=image_path,
        lat=55.7558,  # Примерные координаты Москвы
        lon=37.6173,
        territory_name=os.path.basename(image_path)
    )

    return result.get('grid_path', '') if result.get('success') else ''


# Тестирование
if __name__ == "__main__":
    print("GRID CREATOR TESTING")

    # Тестовые файлы
    test_image = "test_image.jpg"

    if not os.path.exists(test_image):
        print(f"Creating test image: {test_image}")
        # Создаем простое тестовое изображение
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        img[:, :] = [100, 150, 100]  # Зеленый фон

        # Добавляем объекты
        cv2.rectangle(img, (100, 100), (200, 200), [0, 200, 0], -1)  # Зеленый квадрат
        cv2.circle(img, (400, 200), 50, [200, 100, 0], -1)  # Оранжевый круг

        cv2.imwrite(test_image, img)
        print(f"Created: {test_image}")

    # Тестируем создание сетки
    creator = GridCreator()

    print("\n1. Creating simple grid...")
    result1 = creator.create_grid_for_email(
        image_path=test_image,
        lat=55.7558,
        lon=37.6173,
        territory_name="Тестовая территория"  # Русское название будет транслитерировано
    )

    if result1.get('success'):
        print(f"Done: {result1['grid_path']}")

    print("\n2. Creating comparison grid...")
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
        print(f"Done: {result2['comparison_path']}")

    print("\nAll grids created! Ready for notifications.")