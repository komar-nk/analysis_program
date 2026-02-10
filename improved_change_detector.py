
"""
Улучшенный детектор изменений с акцентом на реальные, а не сезонные изменения
"""

import cv2
import numpy as np
from typing import Dict, Any
import os


class ImprovedChangeDetector:
    def __init__(self):
        pass

    def detect_real_changes(self, img1_path: str, img2_path: str) -> Dict[str, Any]:
        """
        Обнаружение реальных изменений с фильтрацией сезонных эффектов
        """
        print("\nУЛУЧШЕННОЕ ОБНАРУЖЕНИЕ РЕАЛЬНЫХ ИЗМЕНЕНИЙ")

        # Загрузка изображений
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)

        if img1 is None or img2 is None:
            return {'error': 'Не удалось загрузить изображения'}

        # 1. Нормализация размера
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = cv2.resize(img1, (w, h))
        img2 = cv2.resize(img2, (w, h))

        print(f"Размер: {w}x{h}")

        print("2. Преобразование в пространство, нечувствительное к освещению...")

        # RGB -> HSV
        img1_hsv = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
        img2_hsv = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

        # Для анализа используем только H (оттенок) и S (насыщенность)
        # V (яркость) игнорируем, так как она зависит от освещения
        img1_hs = img1_hsv[:, :, :2]  # H и S каналы
        img2_hs = img2_hsv[:, :, :2]  # H и S каналы

        # 3. ДЕТЕКЦИЯ СТРУКТУРНЫХ ИЗМЕНЕНИЙ
        print("3. Детекция структурных изменений...")

        # Преобразование в grayscale для структурного анализа
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Нормализация яркости (компенсация освещения)
        mean1 = np.mean(gray1)
        mean2 = np.mean(gray2)
        if mean2 > 0:
            gray2 = cv2.convertScaleAbs(gray2, alpha=mean1 / mean2, beta=0)

        # Поиск особенностей (особенно для растительности)
        print("4. Анализ текстур...")

        # GLCM (Gray Level Co-occurrence Matrix) для анализа текстуры
        # Простая реализация через градиенты
        grad1_x = cv2.Sobel(gray1, cv2.CV_64F, 1, 0, ksize=3)
        grad1_y = cv2.Sobel(gray1, cv2.CV_64F, 0, 1, ksize=3)
        grad1_magnitude = np.sqrt(grad1_x ** 2 + grad1_y ** 2)

        grad2_x = cv2.Sobel(gray2, cv2.CV_64F, 1, 0, ksize=3)
        grad2_y = cv2.Sobel(gray2, cv2.CV_64F, 0, 1, ksize=3)
        grad2_magnitude = np.sqrt(grad2_x ** 2 + grad2_y ** 2)

        # Разница в текстуре (структурные изменения)
        texture_diff = cv2.absdiff(grad1_magnitude, grad2_magnitude)

        # 5. анализ индексов (для леса/растительности)
        print("5. Анализ растительности...")

        # NDVI-like индекс (для спутниковых снимков RGB)
        b1, g1, r1 = cv2.split(img1.astype(np.float32))
        b2, g2, r2 = cv2.split(img2.astype(np.float32))

        # Простой вегетационный индекс
        veg_index1 = (g1 - r1) / (g1 + r1 + 1e-6)
        veg_index2 = (g2 - r2) / (g2 + r2 + 1e-6)

        # Порог для зелени
        veg_mask1 = veg_index1 > 0.1  # Порог для зеленых областей
        veg_mask2 = veg_index2 > 0.1

        # Изменения в растительности
        veg_changes = np.logical_xor(veg_mask1, veg_mask2).astype(np.uint8) * 255

        # 6. Анализ земляных/строительных работ
        print("6. Анализ земляных изменений...")

        # Маска для земли (коричневые тона в HSV)
        # Земляные тона: H=10-30, S=50-200, V=30-150
        lower_earth = np.array([10, 50, 30])
        upper_earth = np.array([30, 200, 150])

        earth_mask1 = cv2.inRange(img1_hsv, lower_earth, upper_earth)
        earth_mask2 = cv2.inRange(img2_hsv, lower_earth, upper_earth)

        # Изменения в земляных покровах
        earth_changes = cv2.absdiff(earth_mask1, earth_mask2)

        # 7. ОБЪЕДИНЕННЫЙ АНАЛИЗ
        print("7. Объединенный анализ изменений...")

        # Объединяем все признаки изменений
        # 1. Текстура (структурные изменения)
        _, texture_thresh = cv2.threshold(texture_diff, 20, 255, cv2.THRESH_BINARY)
        texture_thresh = texture_thresh.astype(np.uint8)

        # 2. Вегетация (растительность)
        veg_changes_clean = cv2.morphologyEx(veg_changes, cv2.MORPH_OPEN,
                                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

        # 3. Земляные работы
        earth_changes_clean = cv2.morphologyEx(earth_changes, cv2.MORPH_OPEN,
                                               cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

        # Объединяем все изменения
        all_changes = cv2.bitwise_or(texture_thresh, veg_changes_clean)
        all_changes = cv2.bitwise_or(all_changes, earth_changes_clean)

        # Удаляем мелкие шумы
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        all_changes = cv2.morphologyEx(all_changes, cv2.MORPH_CLOSE, kernel)
        all_changes = cv2.morphologyEx(all_changes, cv2.MORPH_OPEN, kernel)

        # 8. Фильтрация сезонных изменений
        print("8. Фильтрация сезонных изменений...")

        # Анализ цветовой гаммы (сезонные изменения обычно меняют всю картинку равномерно)
        mean_color1 = np.mean(img1_hs, axis=(0, 1))
        mean_color2 = np.mean(img2_hs, axis=(0, 1))

        # Если средние цвета похожи, но есть локальные изменения - это реальные изменения
        color_diff = np.linalg.norm(mean_color1 - mean_color2)

        # Если цветовая разница большая, но изменения равномерные - возможно сезонные
        change_mask = all_changes > 0
        change_density = np.sum(change_mask) / (w * h)

        is_seasonal = False
        if color_diff > 50 and change_density > 0.3:  # 30% изменений равномерно
            # Проверяем равномерность изменений
            # Делим изображение на 4 части и сравниваем плотность изменений
            h_parts = 2
            w_parts = 2
            part_h = h // h_parts
            part_w = w // w_parts

            densities = []
            for i in range(h_parts):
                for j in range(w_parts):
                    y1 = i * part_h
                    y2 = min((i + 1) * part_h, h)
                    x1 = j * part_w
                    x2 = min((j + 1) * part_w, w)

                    part_mask = change_mask[y1:y2, x1:x2]
                    part_density = np.sum(part_mask) / (part_mask.size if part_mask.size > 0 else 1)
                    densities.append(part_density)

            # Если плотность изменений в разных частях примерно одинаковая - сезонные
            densities_std = np.std(densities)
            if densities_std < 0.05:  # Меньше 5% отклонение
                is_seasonal = True
                print(f"   Обнаружены сезонные изменения (цветовая разница: {color_diff:.1f})")

        total_pixels = w * h
        changed_pixels = np.sum(all_changes > 0)
        change_percentage = (changed_pixels / total_pixels) * 100

        # Определение типа изменений
        change_type = "неизвестно"
        if veg_changes_clean.sum() > texture_thresh.sum() and veg_changes_clean.sum() > earth_changes_clean.sum():
            change_type = "растительность"
        elif earth_changes_clean.sum() > texture_thresh.sum() and earth_changes_clean.sum() > veg_changes_clean.sum():
            change_type = "земляные работы"
        elif texture_thresh.sum() > veg_changes_clean.sum() and texture_thresh.sum() > earth_changes_clean.sum():
            change_type = "структурные"

        # Определение значимости
        if is_seasonal:
            significance = "сезонные"
            real_change_percentage = change_percentage * 0.1  # Снижаем значимость сезонных
        else:
            if change_percentage > 30:
                significance = "критические"
                real_change_percentage = change_percentage
            elif change_percentage > 15:
                significance = "значительные"
                real_change_percentage = change_percentage
            elif change_percentage > 5:
                significance = "умеренные"
                real_change_percentage = change_percentage
            elif change_percentage > 1:
                significance = "незначительные"
                real_change_percentage = change_percentage
            else:
                significance = "отсутствуют"
                real_change_percentage = change_percentage

        print(f"\nРЕЗУЛЬТАТЫ:")
        print(f"   Всего пикселей: {total_pixels:,}")
        print(f"   Изменено пикселей: {changed_pixels:,}")
        print(f"   Процент изменений: {change_percentage:.2f}%")
        print(f"   Реальный процент: {real_change_percentage:.2f}%")
        print(f"   Тип изменений: {change_type}")
        print(f"   Значимость: {significance}")
        print(f"   Сезонные: {'Да' if is_seasonal else 'Нет'}")

        # Создание визуализации
        visualization = self._create_visualization(img2, all_changes, veg_changes_clean,
                                                   earth_changes_clean, texture_thresh,
                                                   change_type, significance, is_seasonal)

        return {
            'success': True,
            'total_pixels': int(total_pixels),
            'changed_pixels': int(changed_pixels),
            'change_percentage': float(change_percentage),
            'real_change_percentage': float(real_change_percentage),
            'change_type': change_type,
            'significance': significance,
            'is_seasonal': is_seasonal,
            'visualization_path': visualization,
            'details': {
                'texture_changes': int(np.sum(texture_thresh > 0)),
                'vegetation_changes': int(np.sum(veg_changes_clean > 0)),
                'earth_changes': int(np.sum(earth_changes_clean > 0)),
                'color_difference': float(color_diff),
                'change_density': float(change_density)
            }
        }

    def _create_visualization(self, img, all_changes, veg_changes, earth_changes,
                              texture_changes, change_type, significance, is_seasonal):
        """Создание визуализации изменений (только английский текст)"""
        h, w = img.shape[:2]
        viz = img.copy()

        # Цвета для разных типов изменений
        if change_type == "растительность":
            overlay_color = (0, 255, 0)  # Зеленый
        elif change_type == "земляные работы":
            overlay_color = (139, 69, 19)  # Коричневый
        elif change_type == "структурные":
            overlay_color = (255, 0, 0)  # Красный
        else:
            overlay_color = (255, 255, 0)  # Желтый

        # Находим контуры изменений
        contours, _ = cv2.findContours(all_changes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Рисуем контуры
        cv2.drawContours(viz, contours, -1, overlay_color, 2)

        # Полупрозрачная заливка
        overlay = viz.copy()
        cv2.drawContours(overlay, contours, -1, overlay_color, -1)
        cv2.addWeighted(overlay, 0.3, viz, 0.7, 0, viz)

        # Английские версии текста для OpenCV
        change_type_en = {
            "растительность": "VEGETATION",
            "земляные работы": "EARTHWORKS",
            "структурные": "STRUCTURAL",
            "строительство": "CONSTRUCTION",
            "водные": "WATER",
            "другие": "OTHER"
        }.get(change_type, "CHANGES")

        significance_en = {
            "значительные": "SIGNIFICANT",
            "умеренные": "MODERATE",
            "незначительные": "MINOR",
            "критические": "CRITICAL"
        }.get(significance, "UNKNOWN")

        text = f"{change_type_en}: {significance_en}"
        if is_seasonal:
            text += " (SEASONAL)"

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2

        # Фон для текста
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        cv2.rectangle(viz, (10, 10), (10 + text_w + 20, 10 + text_h + 20), (0, 0, 0), -1)

        # Текст (английский)
        cv2.putText(viz, text, (20, 10 + text_h + 5), font, font_scale, (255, 255, 255), thickness)

        # Легенда на английском
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
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{change_type_en.lower()}_changes_{timestamp}.jpg"

        cv2.imwrite(filename, viz)
        print(f"Визуализация сохранена: {filename}")
        return filename


# Функция для интеграции с существующей системой
def detect_changes_improved(old_image_path: str, new_image_path: str):
    """Улучшенная функция обнаружения изменений"""
    detector = ImprovedChangeDetector()
    return detector.detect_real_changes(old_image_path, new_image_path)
