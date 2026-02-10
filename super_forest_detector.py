"""
ДЕТЕКТОР ВЫРУБКИ ЛЕСА
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
import os
import time
from scipy import ndimage
import skimage
import warnings

warnings.filterwarnings('ignore')


class SuperForestDetector:
    def __init__(self, sensitivity: float = 1.5):
        """
        Args:
            sensitivity: Коэффициент чувствительности (1.0 - нормально, 2.0 - сверхчувствительно)
        """
        self.sensitivity = sensitivity
        self.min_contour_area = 50  # пикселей

    def detect_changes_aggressive(self, before_path: str, after_path: str) -> Dict[str, Any]:
        """
        обнаружение изменений (военный уровень)
        """

        print("\n🔬 АНАЛИЗ ВЫРУБКИ")
        print("=" * 70)

        # Загрузка с проверкой
        before = cv2.imread(before_path)
        after = cv2.imread(after_path)

        if before is None or after is None:
            return {'error': 'Ошибка загрузки изображений'}

        # Приводим к одинаковому размеру
        h, w = before.shape[:2]
        after = cv2.resize(after, (w, h))

        print(f"Размер: {w}x{h} = {w * h:,} пикселей")
        print(f"Область: {w * 0.01:.1f} x {h * 0.01:.1f} км")

        # ========== ЭТАП 1: ПРЕПРОЦЕССИНГ ==========
        print("\n1. ПРЕПРОЦЕССИНГ (агрессивный)...")

        # Сильная нормализация яркости
        before_norm = self._aggressive_normalization(before)
        after_norm = self._aggressive_normalization(after)

        # Увеличение резкости (сильное)
        before_sharp = self._sharpen_image(before_norm, strength=2.0)
        after_sharp = self._sharpen_image(after_norm, strength=2.0)

        # ========== ЭТАП 2: АНАЛИЗ СТРУКТУРЫ ==========
        print("2. АНАЛИЗ СТРУКТУРЫ (деревья имеют сложную структуру)...")

        # Градиенты (деревья имеют много градиентов)
        grad_before = self._calculate_gradient_magnitude(before_sharp)
        grad_after = self._calculate_gradient_magnitude(after_sharp)

        # Разница градиентов (ВЫРУБКА = потеря структуры)
        grad_diff = cv2.absdiff(grad_before, grad_after)

        # Порог ОЧЕНЬ НИЗКИЙ для улавливания любых изменений
        _, grad_thresh = cv2.threshold(grad_diff, 5, 255, cv2.THRESH_BINARY)

        # ========== ЭТАП 3: АНАЛИЗ ТЕКСТУРЫ ==========
        print("3. АНАЛИЗ ТЕКСТУРЫ (GLCM признаки)...")

        # Локальная бинарная разница
        lbp_before = self._calculate_lbp(before_sharp)
        lbp_after = self._calculate_lbp(after_sharp)
        lbp_diff = cv2.absdiff(lbp_before, lbp_after)

        # ========== ЭТАП 4: АНАЛИЗ ЦВЕТА (ЗЕЛЕНИ) ==========
        print("4. АНАЛИЗ ЦВЕТА (поиск потери зелени)...")

        # Маска зелени (ОЧЕНЬ ШИРОКИЙ диапазон)
        green_loss = self._calculate_green_loss(before, after)

        # ========== ЭТАП 5: АНАЛИЗ КОНТРАСТА ==========
        print("5. АНАЛИЗ КОНТРАСТА (деревья создают контраст)...")

        # Локальный контраст
        contrast_before = self._calculate_local_contrast(before_sharp)
        contrast_after = self._calculate_local_contrast(after_sharp)
        contrast_diff = cv2.absdiff(contrast_before, contrast_after)

        # ========== ЭТАП 6: ОБЪЕДИНЕНИЕ ВСЕХ ПРИЗНАКОВ ==========
        print("6. ОБЪЕДИНЕНИЕ ПРИЗНАКОВ")

        # Взвешенная сумма всех признаков
        combined = np.zeros((h, w), dtype=np.float32)

        # Веса (можно регулировать)
        weights = {
            'gradient': 1.5,  # Структура - самый важный
            'texture': 1.2,  # Текстура
            'green': 2.0,  # Цвет зелени - ВАЖНО!
            'contrast': 1.0  # Контраст
        }

        # Нормализуем и складываем
        if grad_thresh.max() > 0:
            combined += (grad_thresh.astype(np.float32) / 255.0) * weights['gradient']

        if lbp_diff.max() > 0:
            combined += (lbp_diff.astype(np.float32) / 255.0) * weights['texture']

        if green_loss.max() > 0:
            combined += (green_loss.astype(np.float32) / 255.0) * weights['green']

        if contrast_diff.max() > 0:
            combined += (contrast_diff.astype(np.float32) / 255.0) * weights['contrast']

        # Применяем коэффициент чувствительности
        combined *= self.sensitivity

        # Преобразуем в бинарную маску
        combined_normalized = cv2.normalize(combined, None, 0, 255, cv2.NORM_MINMAX)
        combined_8bit = combined_normalized.astype(np.uint8)

        # АДАПТИВНЫЙ порог (очень низкий)
        thresh_mask = cv2.adaptiveThreshold(
            combined_8bit, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # ========== ЭТАП 7: ПОСТОБРАБОТКА ==========
        print("7. ПОСТОБРАБОТКА (объединение мелких изменений)...")

        # СИЛЬНОЕ объединение близких изменений
        kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        thresh_mask = cv2.morphologyEx(thresh_mask, cv2.MORPH_CLOSE, kernel_large)

        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        thresh_mask = cv2.dilate(thresh_mask, kernel_dilate, iterations=2)

        # Удаляем очень мелкие объекты (шум)
        thresh_mask = self._remove_small_objects(thresh_mask, min_size=100)

        # ========== ЭТАП 8: РАСЧЕТ РЕЗУЛЬТАТОВ ==========
        print("8. РАСЧЕТ РЕЗУЛЬТАТОВ (агрессивный)...")

        total_pixels = w * h
        changed_pixels = np.sum(thresh_mask > 0)
        base_percentage = (changed_pixels / total_pixels) * 100

        # АНАЛИЗ ПЛОТНОСТИ ИЗМЕНЕНИЙ
        # Если изменения сгруппированы - это вырубка, если разбросаны - шум
        contours, _ = cv2.findContours(thresh_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Анализ компактности
        if contours:
            # Площади контуров
            areas = [cv2.contourArea(cnt) for cnt in contours]
            avg_area = np.mean(areas)
            max_area = np.max(areas)

            # Если есть крупные изменения (>1% изображения) - точно вырубка
            if max_area > total_pixels * 0.01:  # >1% площади
                is_deforestation = True
                # Увеличиваем процент для крупных изменений
                enhancement_factor = 1.0 + (max_area / total_pixels) * 10
            else:
                is_deforestation = False
                enhancement_factor = 1.0
        else:
            is_deforestation = False
            enhancement_factor = 1.0

        # ДОПОЛНИТЕЛЬНОЕ УСИЛЕНИЕ:
        # 1. Если изменения в зоне зелени
        green_before = self._get_green_mask(before)
        green_after = self._get_green_mask(after)
        green_change = cv2.absdiff(green_before, green_after)

        # Процент изменений в зеленых зонах
        if green_before.sum() > 0:
            green_change_ratio = green_change.sum() / green_before.sum()
        else:
            green_change_ratio = 0

        # 2. Анализ "пустых" зон (вырубка = пустота)
        entropy_before = self._calculate_entropy(before_sharp)
        entropy_after = self._calculate_entropy(after_sharp)
        entropy_change = abs(entropy_before - entropy_after)

        # ========== ЭТАП 9: ФИНАЛЬНЫЙ ПРОЦЕНТ ==========
        print("9. РАСЧЕТ ФИНАЛЬНОГО ПРОЦЕНТА...")

        # БАЗОВЫЙ процент
        final_percentage = base_percentage

        # УСИЛЕНИЕ 1: Если изменения в зеленых зонах
        if green_change_ratio > 0.1:  # >10% зелени изменилось
            final_percentage *= (1.0 + green_change_ratio * 2)
            print(f"   Усиление за зелень: x{1.0 + green_change_ratio * 2:.2f}")

        # УСИЛЕНИЕ 2: Если изменения компактные (крупные пятна)
        if is_deforestation:
            final_percentage *= enhancement_factor
            print(f"   Усиление за компактность: x{enhancement_factor:.2f}")

        # УСИЛЕНИЕ 3: Если потеря энтропии (структуры)
        if entropy_change > 0.5:
            final_percentage *= (1.0 + entropy_change)
            print(f"   Усиление за потерю структуры: x{1.0 + entropy_change:.2f}")

        # УСИЛЕНИЕ 4: Коэффициент чувствительности
        final_percentage *= self.sensitivity

        # Ограничиваем 100%
        final_percentage = min(final_percentage, 100.0)

        # ========== ЭТАП 10: КЛАССИФИКАЦИЯ ==========
        change_type = "неизвестно"
        significance = "неизвестно"

        if green_change_ratio > 0.3 and final_percentage > 20:
            change_type = "МАСШТАБНАЯ ВЫРУБКА ЛЕСА"
            significance = "КРИТИЧЕСКАЯ СИТУАЦИЯ"
        elif green_change_ratio > 0.2 and final_percentage > 15:
            change_type = "значительная вырубка леса"
            significance = "ТРЕБУЕТ ВМЕШАТЕЛЬСТВА"
        elif green_change_ratio > 0.1 and final_percentage > 10:
            change_type = "вырубка леса"
            significance = "заметные изменения"
        elif green_change_ratio > 0.05 and final_percentage > 5:
            change_type = "частичная вырубка"
            significance = "требует наблюдения"
        elif final_percentage > 3:
            change_type = "изменения растительности"
            significance = "незначительные"
        else:
            change_type = "минимальные изменения"
            significance = "в пределах нормы"

        # Уровень серьезности
        if final_percentage > 40:
            change_level = "КАТАСТРОФИЧЕСКИЙ"
            alert_color = (0, 0, 255)  # Красный
        elif final_percentage > 25:
            change_level = "КРИТИЧЕСКИЙ"
            alert_color = (0, 100, 255)  # Оранжевый
        elif final_percentage > 15:
            change_level = "ВЫСОКИЙ"
            alert_color = (0, 200, 255)  # Желтый
        elif final_percentage > 8:
            change_level = "СРЕДНИЙ"
            alert_color = (0, 255, 0)  # Зеленый
        elif final_percentage > 3:
            change_level = "НИЗКИЙ"
            alert_color = (200, 255, 200)  # Светло-зеленый
        else:
            change_level = "МИНИМАЛЬНЫЙ"
            alert_color = (200, 200, 200)  # Серый

        # ========== ЭТАП 11: ВИЗУАЛИЗАЦИЯ ==========
        print("10. СОЗДАНИЕ ВИЗУАЛИЗАЦИИ...")
        viz_path = self._create_aggressive_visualization(
            before, after, thresh_mask, contours,
            change_type, change_level, final_percentage,
            green_change_ratio, alert_color
        )

        # ========== ЭТАП 12: ВЫВОД РЕЗУЛЬТАТОВ ==========
        print("\n" + "=" * 70)
        print("РЕЗУЛЬТАТЫ АНАЛИЗА")
        print("=" * 70)

        results = {
            'success': True,
            'change_type': change_type,
            'change_level': change_level,
            'significance': significance,

            # Проценты
            'base_percentage': float(base_percentage),
            'final_percentage': float(final_percentage),
            'enhancement_factor': float(enhancement_factor),

            # Детали
            'green_change_ratio': float(green_change_ratio),
            'entropy_change': float(entropy_change),
            'changed_pixels': int(changed_pixels),
            'total_pixels': int(total_pixels),
            'contours_count': len(contours),

            # Площади
            'changed_area_pixels': int(changed_pixels),
            'changed_area_sq_m': int(changed_pixels * 100),  # При 10м/пикс
            'changed_area_hectares': changed_pixels * 100 / 10000,

            # Файлы
            'visualization_path': viz_path,
            'mask_path': f"aggressive_mask_{int(time.time())}.png",

            # Статистика
            'statistics': {
                'avg_contour_area': float(np.mean(areas) if areas else 0),
                'max_contour_area': float(np.max(areas) if areas else 0),
                'is_deforestation': is_deforestation,
                'sensitivity_used': self.sensitivity
            }
        }

        # Сохраняем маску
        cv2.imwrite(results['mask_path'], thresh_mask)

        # Выводим подробности
        self._print_detailed_results(results)

        return results

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    def _aggressive_normalization(self, image):
        """Агрессивная нормализация яркости и контраста"""
        # CLAHE (адаптивная гистограмма)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        merged = cv2.merge([l, a, b])
        normalized = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        return normalized

    def _sharpen_image(self, image, strength=1.5):
        """Сильное увеличение резкости"""
        kernel = np.array([[-1, -1, -1],
                           [-1, 9 * strength, -1],
                           [-1, -1, -1]])
        sharpened = cv2.filter2D(image, -1, kernel)
        return sharpened

    def _calculate_gradient_magnitude(self, image):
        """Вычисление магнитуды градиента"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Собелевские градиенты
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        # Магнитуда
        magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)

        # Нормализация
        magnitude_norm = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
        return magnitude_norm.astype(np.uint8)

    def _calculate_lbp(self, image, radius=1, points=8):
        """Локальный бинарный паттерн (текстура)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Простая реализация LBP
        height, width = gray.shape
        lbp = np.zeros((height, width), dtype=np.uint8)

        for i in range(radius, height - radius):
            for j in range(radius, width - radius):
                center = gray[i, j]
                binary = ''

                # 8 соседей
                for k in range(points):
                    angle = 2 * np.pi * k / points
                    x = i + int(radius * np.cos(angle))
                    y = j + int(radius * np.sin(angle))
                    binary += '1' if gray[x, y] >= center else '0'

                lbp[i, j] = int(binary, 2)

        return lbp

    def _calculate_green_loss(self, before, after):
        """Расчет потери зелени"""
        # HSV для лучшего выделения зелени
        before_hsv = cv2.cvtColor(before, cv2.COLOR_BGR2HSV)
        after_hsv = cv2.cvtColor(after, cv2.COLOR_BGR2HSV)

        # ШИРОКИЙ диапазон зеленого (захватывает все оттенки)
        lower_green1 = np.array([25, 30, 30])
        upper_green1 = np.array([95, 255, 255])

        # Дополнительный диапазон для светло-зеленого
        lower_green2 = np.array([25, 20, 100])
        upper_green2 = np.array([95, 100, 255])

        # Маски
        mask1_before = cv2.inRange(before_hsv, lower_green1, upper_green1)
        mask2_before = cv2.inRange(before_hsv, lower_green2, upper_green2)
        green_before = cv2.bitwise_or(mask1_before, mask2_before)

        mask1_after = cv2.inRange(after_hsv, lower_green1, upper_green1)
        mask2_after = cv2.inRange(after_hsv, lower_green2, upper_green2)
        green_after = cv2.bitwise_or(mask1_after, mask2_after)

        # Потеря зелени (было зелено, стало не зелено)
        green_loss = cv2.bitwise_and(green_before, cv2.bitwise_not(green_after))

        # Улучшаем маску
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        green_loss = cv2.morphologyEx(green_loss, cv2.MORPH_CLOSE, kernel)

        return green_loss

    def _get_green_mask(self, image):
        """Простая маска зелени"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        return cv2.inRange(hsv, lower_green, upper_green)

    def _calculate_local_contrast(self, image, block_size=31):
        """Локальный контраст"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Локальное стандартное отклонение = контраст
        contrast = ndimage.generic_filter(
            gray.astype(np.float32),
            np.std,
            size=block_size
        )

        # Нормализация
        contrast_norm = cv2.normalize(contrast, None, 0, 255, cv2.NORM_MINMAX)
        return contrast_norm.astype(np.uint8)

    def _calculate_entropy(self, image, window_size=7):
        """Энтропия изображения (мера сложности/структуры)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        entropy = np.zeros_like(gray, dtype=np.float32)

        half = window_size // 2
        for i in range(half, gray.shape[0] - half):
            for j in range(half, gray.shape[1] - half):
                window = gray[i - half:i + half + 1, j - half:j + half + 1]
                hist = np.histogram(window, bins=256, range=(0, 256))[0]
                hist = hist / hist.sum()
                entropy[i, j] = -np.sum(hist * np.log2(hist + 1e-10))

        return np.mean(entropy)

    def _remove_small_objects(self, mask, min_size=100):
        """Удаление мелких объектов"""
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)

        result = np.zeros_like(mask)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_size:
                result[labels == i] = 255

        return result

    def _create_aggressive_visualization(self, before: object, after: object, mask: object, contours: object,
                                         change_type: object, change_level: object, percentage: object,
                                         green_ratio: object, alert_color: object) -> str:
        """Создание агрессивной визуализации"""
        h, w = before.shape[:2]

        # Комбинированное изображение
        viz = after.copy()

        # 1. Контуры изменений (толстые, красные)
        cv2.drawContours(viz, contours, -1, alert_color, 3)

        # 2. Полупрозрачная заливка
        overlay = viz.copy()
        for cnt in contours:
            cv2.drawContours(overlay, [cnt], -1, alert_color, -1)
        cv2.addWeighted(overlay, 0.4, viz, 0.6, 0, viz)

        # 3. ТЕКСТ ПРЯМО НА ИЗОБРАЖЕНИИ (крупный, жирный)
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Основной заголовок
        main_text = f"{change_type.upper()}"
        cv2.putText(viz, main_text, (20, 40), font, 1.2, (0, 0, 0), 4)
        cv2.putText(viz, main_text, (20, 40), font, 1.2, alert_color, 2)

        # Процент
        percent_text = f"ИЗМЕНЕНИЯ: {percentage:.1f}%"
        cv2.putText(viz, percent_text, (20, 80), font, 1.0, (0, 0, 0), 4)
        cv2.putText(viz, percent_text, (20, 80), font, 1.0, (255, 255, 255), 2)

        # Уровень
        level_text = f"УРОВЕНЬ: {change_level}"
        cv2.putText(viz, level_text, (20, 120), font, 1.0, (0, 0, 0), 4)
        cv2.putText(viz, level_text, (20, 120), font, 1.0, (255, 255, 0), 2)

        # 4. Легенда
        legend_y = h - 150
        cv2.rectangle(viz, (10, legend_y), (400, h - 10), (0, 0, 0, 200), -1)
        cv2.rectangle(viz, (10, legend_y), (400, h - 10), (255, 255, 255), 2)

        legend_items = [
            (" КРАСНЫЙ - ОБЛАСТЬ ВЫРУБКИ", alert_color),
            (" ПЛОЩАДЬ - МАСШТАБ ИЗМЕНЕНИЙ", (255, 255, 255)),
            (" ПОТЕРЯ ЗЕЛЕНИ - {:.1f}%".format(green_ratio * 100), (0, 255, 0))
        ]

        for i, (text, color) in enumerate(legend_items):
            y_pos = legend_y + 40 + i * 35
            cv2.putText(viz, text, (20, y_pos), font, 0.6, color, 2)

        # 5. Шкала серьезности
        cv2.rectangle(viz, (w - 200, 10), (w - 10, 100), (0, 0, 0, 180), -1)
        cv2.putText(viz, "ШКАЛА СЕРЬЕЗНОСТИ:", (w - 190, 30), font, 0.5, (255, 255, 255), 1)

        if percentage > 40:
            severity = " КАТАСТРОФИЧЕСКИЙ"
            color = (0, 0, 255)
        elif percentage > 25:
            severity = " КРИТИЧЕСКИЙ"
            color = (0, 100, 255)
        elif percentage > 15:
            severity = "️ ВЫСОКИЙ"
            color = (0, 200, 255)
        elif percentage > 8:
            severity = " СРЕДНИЙ"
            color = (0, 255, 0)
        elif percentage > 3:
            severity = " НИЗКИЙ"
            color = (200, 255, 200)
        else:
            severity = " МИНИМАЛЬНЫЙ"
            color = (200, 200, 200)

        cv2.putText(viz, severity, (w - 190, 60), font, 0.7, color, 2)
        cv2.putText(viz, f"{percentage:.1f}%", (w - 190, 90), font, 0.7, (255, 255, 255), 2)

        # Сохраняем
        timestamp = int(time.time())
        filename = f"SUPER_AGGRESSIVE_{timestamp}.jpg"
        cv2.imwrite(filename, viz)

        print(f" Визуализация: {filename}")
        return filename

    def _print_detailed_results(self, results):
        """Детальный вывод результатов"""
        print(f"\n ДЕТАЛЬНАЯ СТАТИСТИКА:")
        print(f"   {'=' * 40}")
        print(f"    Базовый процент: {results['base_percentage']:.1f}%")
        print(f"    Финальный процент: {results['final_percentage']:.1f}%")
        print(f"    Коэффициент усиления: x{results['enhancement_factor']:.2f}")
        print(f"    Потеря зелени: {results['green_change_ratio'] * 100:.1f}%")
        print(f"    Контуров изменений: {results['contours_count']}")
        print(f"    Площадь изменений: {results['changed_area_hectares']:.2f} га")
        print(f"    Уровень серьезности: {results['change_level']}")

        if results['final_percentage'] > 25:
            print(f"\n   🚨🚨🚨 ВНИМАНИЕ: КРИТИЧЕСКИЕ ИЗМЕНЕНИЯ! 🚨🚨🚨")
            print(f"   Вероятно, обнаружена масштабная вырубка леса!")
            print(f"   Рекомендуется немедленная проверка территории.")

        print(f"\n   💾 Файлы:")
        print(f"   • Визуализация: {results['visualization_path']}")
        print(f"   • Маска изменений: {results['mask_path']}")
        print(f"   {'=' * 40}")


# ========== ИНТЕРФЕЙС ДЛЯ ИНТЕГРАЦИИ ==========

def detect_changes_super_aggressive(before_path: str, after_path: str,
                                    sensitivity: float = 1.5) -> Dict[str, Any]:
    """
    Интерфейс для супер-агрессивного детектора

    Args:
        before_path: Путь к изображению "до"
        after_path: Путь к изображению "после"
        sensitivity: Чувствительность (1.0-3.0)
    """
    detector = SuperForestDetector(sensitivity=sensitivity)
    return detector.detect_changes_aggressive(before_path, after_path)
