
"""
Модуль для анализа спутниковых изображений с координатной сеткой
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import cv2
from datetime import datetime
import math
import traceback


class GridAnalyzer:
    def __init__(self, grid_size=32):
        """
        Инициализация анализатора сетки

        Args:
            grid_size (int): Размер ячейки сетки в пикселях (по умолчанию 32)
        """
        self.grid_size = grid_size
        self.output_dir = Path("grid_analysis")
        self.output_dir.mkdir(exist_ok=True)
        print(f"GridAnalyzer инициализирован с размером сетки: {grid_size}px")

    def analyze_territory_with_grid(self, territory_info, old_image_path, new_image_path, grid_size=None):
        """
        Анализ территории с координатной сеткой

        Args:
            territory_info (dict): Информация о территории
            old_image_path (str): Путь к старому изображению
            new_image_path (str): Путь к новому изображению
            grid_size (int, optional): Размер сетки. Если None, использует self.grid_size

        Returns:
            dict: Результаты анализа
        """
        try:
            # Используем указанный размер сетки или значение по умолчанию
            current_grid_size = grid_size if grid_size is not None else self.grid_size

            print(f"\nНачинаю анализ территории '{territory_info.get('name', 'N/A')}'...")
            print(f"Размер сетки: {current_grid_size}x{current_grid_size} пикселей")

            # Проверяем существование файлов
            if not os.path.exists(old_image_path):
                return {'success': False, 'error': f'Старый файл не найден: {old_image_path}'}
            if not os.path.exists(new_image_path):
                return {'success': False, 'error': f'Новый файл не найден: {new_image_path}'}

            # Загружаем изображения
            print("Загрузка изображений...")
            old_img = Image.open(old_image_path)
            new_img = Image.open(new_image_path)

            # Проверяем размеры
            old_size = old_img.size
            new_size = new_img.size
            if old_size != new_size:
                print(f"Размеры изображений не совпадают: {old_size} != {new_size}")
                return {'success': False, 'error': f'Размеры изображений не совпадают: {old_size} != {new_size}'}

            print(f"Размер изображений: {old_size[0]}x{old_size[1]} пикселей")

            # Создаем сетку
            print(f"Создание сетки...")
            grid_info = self._create_grid(old_size, current_grid_size)
            print(f"Сетка создана: {grid_info['cells_x']}x{grid_info['cells_y']} ячеек")

            # Анализируем изменения
            print("Анализ изменений в ячейках...")
            analysis_results = self._analyze_grid_changes(old_img, new_img, grid_info, territory_info, current_grid_size)

            # Создаем визуализацию
            print("Создание визуализации...")
            visualization_path = self._create_visualization(old_img, new_img, grid_info, analysis_results, territory_info, current_grid_size)

            # Создаем тепловую карту
            print("Создание тепловой карты...")
            heatmap_path = self._create_heatmap(analysis_results, territory_info, grid_info)

            # Создаем изображение с сеткой
            print("Создание изображения с сеткой...")
            grid_image_path = self._create_grid_image(old_img, grid_info, territory_info, current_grid_size)

            # Экспортируем результаты
            print("Экспорт результатов...")
            export_path = self._export_results(analysis_results, territory_info, grid_info)

            print("Анализ завершен успешно!")

            return {
                'success': True,
                'visualization_path': str(visualization_path),
                'heatmap_path': str(heatmap_path),
                'grid_image_path': str(grid_image_path),
                'export_path': str(export_path),
                'total_cells': grid_info['total_cells'],
                'changed_cells': analysis_results['changed_cells'],
                'analysis_summary': analysis_results['summary']
            }

        except Exception as e:
            print(f"Ошибка при анализе: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def create_grid_image(self, image_path, lat_center, lon_center, area_km=2.0, grid_size=None):
        """
        Создание изображения с наложенной координатной сеткой

        Args:
            image_path (str): Путь к изображению
            lat_center (float): Широта центра изображения
            lon_center (float): Долгота центра изображения
            area_km (float): Размер области в километрах
            grid_size (int, optional): Размер сетки

        Returns:
            dict: Результаты операции
        """
        try:
            current_grid_size = grid_size if grid_size is not None else self.grid_size

            if not os.path.exists(image_path):
                return {'success': False, 'error': f'Файл не найден: {image_path}'}

            print(f"Загрузка изображения: {os.path.basename(image_path)}")
            image = Image.open(image_path)

            # Создаем сетку
            grid_info = self._create_grid(image.size, current_grid_size)

            # Добавляем географическую информацию
            geo_bounds = self._calculate_geo_bounds(image.size, lat_center, lon_center, area_km)
            grid_info['geo_bounds'] = geo_bounds

            # Создаем изображение с сеткой
            result_path = self._draw_grid_on_image(image, grid_info, geo_bounds)

            return {
                'success': True,
                'grid_image_path': str(result_path),
                'grid_info': grid_info,
                'geo_bounds': geo_bounds
            }

        except Exception as e:
            print(f"Ошибка создания сетки: {e}")
            return {'success': False, 'error': str(e)}

    def analyze_changes_with_grid(self, image1_path, image2_path, grid_info):
        """
        Анализ изменений между двумя изображениями с использованием существующей сетки

        Args:
            image1_path (str): Путь к первому изображению (старому)
            image2_path (str): Путь ко второму изображению (новому)
            grid_info (dict): Информация о сетке

        Returns:
            dict: Результаты анализа
        """
        try:
            if not os.path.exists(image1_path) or not os.path.exists(image2_path):
                return {'success': False, 'error': 'Один из файлов не найден'}

            img1 = Image.open(image1_path)
            img2 = Image.open(image2_path)

            if img1.size != img2.size:
                return {'success': False, 'error': 'Размеры изображений не совпадают'}

            # Создаем заглушку territory_info для совместимости
            territory_info = {
                'name': 'Сравнение изображений',
                'latitude': 0.0,
                'longitude': 0.0,
                'description': 'Сравнение двух изображений'
            }

            analysis_results = self._analyze_grid_changes(img1, img2, grid_info, territory_info, grid_info['grid_size'])

            return {
                'success': True,
                'analysis_summary': analysis_results['summary'],
                'changed_cells': analysis_results['changed_cells']
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def print_detailed_report(self, analysis_results):
        """
        Печать детального отчета по анализу

        Args:
            analysis_results (dict): Результаты анализа
        """
        if not analysis_results or not analysis_results.get('success', False):
            print("Нет данных для отчета")
            return

        summary = analysis_results.get('analysis_summary', {})
        changed_cells = analysis_results.get('changed_cells', [])

        print("\n" + "=" * 60)
        print("ДЕТАЛЬНЫЙ ОТЧЕТ ПО АНАЛИЗУ")
        print("=" * 60)

        print(f"\nОБЩАЯ СТАТИСТИКА:")
        total_cells = summary.get('total_cells', 0)
        changed_count = len(changed_cells)
        print(f"   Всего ячеек: {total_cells}")
        print(f"   Измененных ячеек: {changed_count}")
        if total_cells > 0:
            print(f"   Процент изменений: {changed_count / total_cells * 100:.1f}%")

        if changed_cells:
            print(f"\nРАСПРЕДЕЛЕНИЕ ПО ТИПАМ ИЗМЕНЕНИЙ:")
            types = {}
            for cell in changed_cells:
                change_type = cell.get('change_type', 'unknown')
                types[change_type] = types.get(change_type, 0) + 1

            for change_type, count in types.items():
                percentage = count / changed_count * 100 if changed_count > 0 else 0
                print(f"   {change_type}: {count} ячеек ({percentage:.1f}%)")

        print(f"\nСТАТИСТИКА ИЗМЕНЕНИЙ:")
        print(f"   Среднее изменение: {summary.get('avg_pixel_change', 0):.1f}%")
        print(f"   Максимальное изменение: {summary.get('max_pixel_change', 0):.1f}%")
        print(f"   Минимальное изменение: {summary.get('min_pixel_change', 0):.1f}%")

        if changed_cells:
            print(f"\nТОП-5 НАИБОЛЕЕ ИЗМЕНЕННЫХ ЯЧЕЕК:")
            sorted_cells = sorted(changed_cells, key=lambda x: x.get('pixel_change_percent', 0), reverse=True)[:5]

            for i, cell in enumerate(sorted_cells, 1):
                percent = cell.get('pixel_change_percent', 0)
                cell_id = cell.get('id', 'N/A')
                change_type = cell.get('change_type', 'unknown')
                lat = cell.get('lat', 0)
                lon = cell.get('lon', 0)

                print(f"\n   {i}. Ячейка {cell_id}:")
                print(f"      Изменения: {percent:.1f}%")
                print(f"      Тип: {change_type}")
                print(f"      Координаты: {lat:.6f}°, {lon:.6f}°")
                print(f"      Измененных пикселей: {cell.get('changed_pixels', 0)}/{cell.get('total_pixels', 0)}")

                # Google Maps ссылка
                if lat != 0 and lon != 0:
                    print(f"      Карта: https://www.google.com/maps?q={lat},{lon}")

    def export_results_to_json(self, analysis_results, filename=None):
        """
        Экспорт результатов в JSON файл

        Args:
            analysis_results (dict): Результаты анализа
            filename (str, optional): Имя файла

        Returns:
            str: Путь к сохраненному файлу или None при ошибке
        """
        if not analysis_results or not analysis_results.get('success', False):
            print("Нет данных для экспорта")
            return None

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"grid_analysis_{timestamp}.json"

        output_path = self.output_dir / filename

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Преобразуем numpy значения в стандартные типы Python
                serializable_results = self._make_serializable(analysis_results)
                json.dump(serializable_results, f, ensure_ascii=False, indent=2)

            print(f"Результаты экспортированы в: {output_path}")
            return str(output_path)

        except Exception as e:
            print(f"Ошибка экспорта: {e}")
            return None

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def _create_grid(self, image_size, grid_size):
        """Создание координатной сетки"""
        width, height = image_size
        cells_x = width // grid_size
        cells_y = height // grid_size

        grid_cells = []
        for y in range(cells_y):
            for x in range(cells_x):
                cell = {
                    'id': f'{x}_{y}',
                    'x': x * grid_size,
                    'y': y * grid_size,
                    'width': grid_size,
                    'height': grid_size,
                    'center_x': x * grid_size + grid_size // 2,
                    'center_y': y * grid_size + grid_size // 2
                }
                grid_cells.append(cell)

        return {
            'cells_x': cells_x,
            'cells_y': cells_y,
            'total_cells': cells_x * cells_y,
            'grid_size': grid_size,
            'cells': grid_cells
        }

    def _calculate_geo_bounds(self, image_size, lat_center, lon_center, area_km):
        """Расчет географических границ изображения"""
        width, height = image_size

        km_per_degree_lat = 111.0
        km_per_degree_lon = 111.0 * math.cos(math.radians(lat_center))

        lat_span = area_km / km_per_degree_lat
        lon_span = area_km / km_per_degree_lon

        return {
            'north': lat_center + lat_span / 2,
            'south': lat_center - lat_span / 2,
            'east': lon_center + lon_span / 2,
            'west': lon_center - lon_span / 2,
            'center_lat': lat_center,
            'center_lon': lon_center,
            'area_km': area_km,
            'lat_span': lat_span,
            'lon_span': lon_span
        }

    def _calculate_coordinates(self, x, y, img_width, img_height, geo_bounds):
        """Расчет географических координат для пикселя"""
        # Нормализованные координаты (0-1)
        norm_x = x / img_width
        norm_y = y / img_height

        # Переводим в географические координаты
        lon = geo_bounds['west'] + norm_x * (geo_bounds['east'] - geo_bounds['west'])
        lat = geo_bounds['south'] + norm_y * (geo_bounds['north'] - geo_bounds['south'])

        return lat, lon

    def _analyze_grid_changes(self, old_img, new_img, grid_info, territory_info, grid_size):
        """Анализ изменений в каждой ячейке сетки"""
        old_array = np.array(old_img.convert('RGB'))
        new_array = np.array(new_img.convert('RGB'))

        # Рассчитываем географические границы
        geo_bounds = self._calculate_geo_bounds(
            old_img.size,
            territory_info.get('latitude', 0.0),
            territory_info.get('longitude', 0.0),
            2.0  # Стандартная площадь 2x2 км
        )

        changed_cells = []
        total_pixel_changes = []

        print(f"Анализ {grid_info['total_cells']} ячеек...")

        for i, cell in enumerate(grid_info['cells']):
            # Прогресс
            if i % 100 == 0:
                print(f"   Прогресс: {i}/{grid_info['total_cells']} ячеек...")

            # Вырезаем ячейку из изображений
            old_cell = old_array[
                cell['y']:cell['y'] + cell['height'],
                cell['x']:cell['x'] + cell['width']
            ]
            new_cell = new_array[
                cell['y']:cell['y'] + cell['height'],
                cell['x']:cell['x'] + cell['width']
            ]

            # Вычисляем разницу
            diff = cv2.absdiff(old_cell, new_cell)
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)

            # Порог для определения изменений
            _, threshold = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)

            # Процент измененных пикселей
            changed_pixels = np.sum(threshold > 0)
            total_pixels = threshold.size
            change_percent = (changed_pixels / total_pixels) * 100

            if change_percent > 5:  # Порог 5%
                # Рассчитываем географические координаты для ячейки
                lat, lon = self._calculate_coordinates(
                    cell['center_x'], cell['center_y'],
                    old_img.size[0], old_img.size[1],
                    geo_bounds
                )

                # Определяем тип изменений
                change_type = self._determine_change_type(old_cell, new_cell, change_percent)

                changed_cell = {
                    **cell,
                    'lat': float(lat),
                    'lon': float(lon),
                    'pixel_change_percent': float(change_percent),
                    'changed_pixels': int(changed_pixels),
                    'total_pixels': int(total_pixels),
                    'change_type': change_type
                }
                changed_cells.append(changed_cell)
                total_pixel_changes.append(change_percent)

        print(f"Анализ завершен. Найдено {len(changed_cells)} измененных ячеек.")

        # Статистика
        summary = {
            'total_cells': grid_info['total_cells'],
            'changed_cells': len(changed_cells),
            'avg_pixel_change': float(np.mean(total_pixel_changes) if total_pixel_changes else 0),
            'max_pixel_change': float(max(total_pixel_changes) if total_pixel_changes else 0),
            'min_pixel_change': float(min(total_pixel_changes) if total_pixel_changes else 0),
            'lighting_changes': sum(1 for cell in changed_cells if cell['change_type'] == 'lighting'),
            'color_changes': sum(1 for cell in changed_cells if cell['change_type'] == 'color'),
            'structural_changes': sum(1 for cell in changed_cells if cell['change_type'] == 'structural')
        }

        return {
            'changed_cells': changed_cells,
            'summary': summary
        }

    def _determine_change_type(self, old_cell, new_cell, change_percent):
        """Определение типа изменений"""
        # Упрощенная логика определения типа изменений
        if change_percent > 50:
            return 'structural'
        elif change_percent > 20:
            return 'color'
        else:
            return 'lighting'

    def _draw_grid_on_image(self, image, grid_info, geo_bounds):
        """Рисует сетку на изображении"""
        grid_img = image.copy()
        draw = ImageDraw.Draw(grid_img)

        # Пытаемся загрузить шрифт
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            except:
                font = ImageFont.load_default()

        # Рисуем сетку
        for cell in grid_info['cells']:
            # Рисуем прямоугольник ячейки
            draw.rectangle(
                [cell['x'], cell['y'],
                 cell['x'] + cell['width'], cell['y'] + cell['height']],
                outline='red', width=1
            )

        # Добавляем координаты только для некоторых ячеек чтобы не загромождать
        for cell in grid_info['cells']:
            if cell['x'] % (grid_info['grid_size'] * 4) == 0 and cell['y'] % (grid_info['grid_size'] * 4) == 0:
                lat, lon = self._calculate_coordinates(
                    cell['center_x'], cell['center_y'],
                    image.size[0], image.size[1],
                    geo_bounds
                )

                # Форматируем координаты
                lat_str = f"{lat:.4f}°"
                lon_str = f"{lon:.4f}°"

                draw.text(
                    (cell['x'] + 2, cell['y'] + 2),
                    f"{lat_str}\n{lon_str}",
                    fill='yellow',
                    font=font
                )

        # Добавляем заголовок
        title = f"Координатная сетка {grid_info['grid_size']}px"
        center_coords = f"Центр: {geo_bounds['center_lat']:.4f}°, {geo_bounds['center_lon']:.4f}°"
        area_info = f"Область: {geo_bounds['area_km']}x{geo_bounds['area_km']} км"

        draw.text(
            (10, 10),
            f"{title}\n{center_coords}\n{area_info}",
            fill='white',
            font=font,
            stroke_width=1,
            stroke_fill='black'
        )

        # Сохраняем изображение
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"grid_{grid_info['grid_size']}px_{timestamp}.png"
        output_path = self.output_dir / filename
        grid_img.save(output_path)

        return output_path

    def _create_visualization(self, img, all_changes, veg_changes, earth_changes,
                              texture_changes, change_type, significance, is_seasonal):
        """Создание визуализации изменений"""
        h, w = img.shape[:2]
        viz = img.copy()

        # Цвета для разных типов изменений
        if change_type == "растительность":
            overlay_color = (0, 255, 0)  # Зеленый
            change_type_eng = "vegetation"
        elif change_type == "земляные работы":
            overlay_color = (139, 69, 19)  # Коричневый
            change_type_eng = "earthworks"
        elif change_type == "структурные":
            overlay_color = (255, 0, 0)  # Красный
            change_type_eng = "structural"
        else:
            overlay_color = (255, 255, 0)  # Желтый
            change_type_eng = change_type

        # Перевод значимости на английский
        significance_dict = {
            "критические": "critical",
            "значительные": "significant",
            "умеренные": "moderate",
            "незначительные": "minor",
            "отсутствуют": "none",
            "сезонные": "seasonal"
        }
        significance_eng = significance_dict.get(significance, significance)

        # Находим контуры изменений
        contours, _ = cv2.findContours(all_changes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Рисуем контуры
        cv2.drawContours(viz, contours, -1, overlay_color, 2)

        # Полупрозрачная заливка
        overlay = viz.copy()
        cv2.drawContours(overlay, contours, -1, overlay_color, -1)
        cv2.addWeighted(overlay, 0.3, viz, 0.7, 0, viz)

        # Добавляем текст (Английский)
        text = f"{change_type_eng.upper()}: {significance_eng}"
        if is_seasonal:
            text += " (seasonal)"

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2

        # Фон для текста
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        cv2.rectangle(viz, (10, 10), (10 + text_w + 10, 10 + text_h + 20), (0, 0, 0), -1)

        # Текст
        cv2.putText(viz, text, (20, 10 + text_h + 5), font, font_scale, (255, 255, 255), thickness)

        # Легенда (Английский)
        legend_y = h - 150
        cv2.rectangle(viz, (10, legend_y), (300, h - 10), (0, 0, 0, 180), -1)
        cv2.rectangle(viz, (10, legend_y), (300, h - 10), (255, 255, 255), 1)

        legend_items = [
            ("Vegetation", (0, 255, 0)),
            ("Earthworks", (139, 69, 19)),
            ("Structural", (255, 0, 0)),
            ("Seasonal", (255, 255, 0))
        ]

        for i, (label, color) in enumerate(legend_items):
            y = legend_y + 30 + i * 30
            cv2.rectangle(viz, (20, y - 10), (40, y + 10), color, -1)
            cv2.putText(viz, label, (50, y + 5), font, 0.5, (255, 255, 255), 1)

        # Сохраняем
        import time
        timestamp = int(time.time())
        filename = f"real_changes_{timestamp}.jpg"
        cv2.imwrite(filename, viz)

        print(f"Visualization saved: {filename}")
        return filename

    def _create_heatmap(self, analysis_results, territory_info, grid_info):
        """Создание тепловой карты изменений"""
        if not analysis_results['changed_cells']:
            # Создаем пустую тепловую карту
            heatmap = Image.new('RGB', (400, 400), color='white')
            draw = ImageDraw.Draw(heatmap)
            draw.text((100, 180), "Нет значительных изменений", fill='black')
        else:
            # Создаем тепловую карту
            size = min(600, grid_info['cells_x'] * 15, grid_info['cells_y'] * 15)
            heatmap = Image.new('RGB', (size, size), color=(240, 240, 240))
            draw = ImageDraw.Draw(heatmap)

            # Масштабируем координаты
            scale_x = size / grid_info['cells_x']
            scale_y = size / grid_info['cells_y']

            for cell in analysis_results['changed_cells']:
                # Получаем индексы ячейки из ID
                x_idx, y_idx = map(int, cell['id'].split('_'))

                # Масштабируем координаты
                x = int(x_idx * scale_x)
                y = int(y_idx * scale_y)
                cell_size = max(3, int(min(scale_x, scale_y) * 0.9))

                # Цвет в зависимости от процента изменений
                intensity = min(255, int(cell['pixel_change_percent'] * 2.55))

                if cell['change_type'] == 'structural':
                    color = (255, 100, 100)  # Красный
                elif cell['change_type'] == 'color':
                    color = (255, 255, 100)  # Желтый
                else:
                    color = (100, 100, 255)  # Синий

                # Делаем цвет более насыщенным для больших изменений
                if cell['pixel_change_percent'] > 50:
                    color = tuple(min(255, c + 50) for c in color)

                draw.rectangle(
                    [x, y, x + cell_size, y + cell_size],
                    fill=color,
                    outline='black',
                    width=1
                )

            # Добавляем легенду
            draw.text((10, 10), "Тепловая карта изменений", fill='black')
            draw.text((10, size - 50), "Красный - Структурные, Желтый - Цветовые, Синий - Освещение", fill='black')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        territory_name = territory_info.get('name', 'unknown').replace(' ', '_')
        filename = f"heatmap_{territory_name}_{timestamp}.png"
        output_path = self.output_dir / filename
        heatmap.save(output_path)

        return output_path

    def _create_grid_image(self, image, grid_info, territory_info, grid_size):
        """Создание изображения с наложенной сеткой"""
        geo_bounds = {
            'center_lat': territory_info.get('latitude', 0.0),
            'center_lon': territory_info.get('longitude', 0.0),
            'area_km': 2.0,
            'north': territory_info.get('latitude', 0.0) + 0.01,
            'south': territory_info.get('latitude', 0.0) - 0.01,
            'east': territory_info.get('longitude', 0.0) + 0.01,
            'west': territory_info.get('longitude', 0.0) - 0.01
        }

        return self._draw_grid_on_image(image, grid_info, geo_bounds)

    def _export_results(self, analysis_results, territory_info, grid_info):
        """Экспорт результатов в JSON"""
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'territory_name': territory_info.get('name', 'Unknown'),
                'grid_size': grid_info['grid_size'],
                'total_cells': grid_info['total_cells']
            },
            'territory_info': territory_info,
            'grid_info': {
                'cells_x': grid_info['cells_x'],
                'cells_y': grid_info['cells_y'],
                'grid_size': grid_info['grid_size']
            },
            'analysis_summary': analysis_results['summary'],
            'changed_cells': analysis_results['changed_cells']
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        territory_name = territory_info.get('name', 'unknown').replace(' ', '_')
        filename = f"results_{territory_name}_{timestamp}.json"
        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self._make_serializable(export_data), f, ensure_ascii=False, indent=2)

        return output_path

    def _make_serializable(self, obj):
        """Преобразует объект в сериализуемый формат"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)
        else:
            return obj


# Вспомогательная функция для удобства
def analyze_territory_with_grid(territory_info, old_image_path, new_image_path, grid_size=32):
    """
    Вспомогательная функция для анализа территории с сеткой

    Args:
        territory_info (dict): Информация о территории
        old_image_path (str): Путь к старому изображению
        new_image_path (str): Путь к новому изображению
        grid_size (int): Размер ячейки сетки

    Returns:
        dict: Результаты анализа
    """
    analyzer = GridAnalyzer(grid_size=grid_size)
    return analyzer.analyze_territory_with_grid(
        territory_info=territory_info,
        old_image_path=old_image_path,
        new_image_path=new_image_path,
        grid_size=grid_size
    )

if __name__ == "__main__":
    print("Grid Analyzer Module")
    print("=" * 40)
    print("Этот модуль предоставляет функционал для анализа")
    print("спутниковых изображений с координатной сеткой.")
    print("\nДля использования импортируйте GridAnalyzer:")
    print("  from grid_analyzer import GridAnalyzer")
    print("\nПример:")
    print("  analyzer = GridAnalyzer(grid_size=32)")
    print("  results = analyzer.analyze_territory_with_grid(...)")