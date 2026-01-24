"""
Главное меню системы мониторинга с поддержкой координатной сетки
"""

import sys
import os
from pathlib import Path

# Убираем неправильный импорт self
# import self

# Добавляем текущую директорию в путь для импортов
sys.path.append(str(Path(__file__).parent))

from database import Database
from gee_client import GEEClient
from change_detector import ChangeDetector
from grid_analyzer import GridAnalyzer  # Убираем импорт analyze_territory_with_grid


def print_header():
    """Печать заголовка"""
    print("\n" + "=" * 60)
    print("🎯 СИСТЕМА МОНИТОРИНГА С КООРДИНАТНОЙ СЕТКОЙ")
    print("=" * 60)


def print_menu():
    """Печать главного меню"""
    print("\nГЛАВНОЕ МЕНЮ:")
    print("1. Управление территориями")
    print("2. Получить спутниковое изображение")
    print("3. Анализ изображений (обычный)")
    print("4. Анализ с координатной сеткой")
    print("5. Мониторинг и детекция изменений")
    print("6. Настройки и информация")
    print("0. Выход")


class SatelliteMonitorApp:
    def __init__(self):
        self.db = Database()
        self.gee_client = GEEClient()
        self.change_detector = ChangeDetector(self.db, self.gee_client)
        self.grid_analyzer = GridAnalyzer()

    def grid_analysis_menu(self):
        """Меню анализа с координатной сеткой"""
        while True:
            print("\n" + "=" * 60)
            print("АНАЛИЗ С КООРДИНАТНОЙ СЕТКОЙ")
            print("=" * 60)
            print("\n1. Проанализировать территорию с сеткой")
            print("2. Создать сетку для изображения")
            print("3. Сравнить два изображения с сеткой")
            print("4. Показать пример сетки")
            print("0. Назад")

            choice = input("\nВыберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.analyze_territory_with_grid()
            elif choice == '2':
                self.create_grid_for_image()
            elif choice == '3':
                self.compare_images_with_grid()
            elif choice == '4':
                self.show_grid_example()
            else:
                print("Неверный выбор")

            input("\nНажмите Enter чтобы продолжить...")

    def analyze_territory_with_grid(self):
        """Анализ территории с координатной сеткой"""
        print("\n" + "=" * 60)
        print("АНАЛИЗ ТЕРРИТОРИИ С КООРДИНАТНОЙ СЕТКОЙ")
        print("=" * 60)

        # Выбираем территорию
        territories = self.db.get_all_territories()
        if not territories:
            print("\nНет территорий для анализа")
            print("Сначала добавьте территории через меню 'Управление территориями'")
            return

        print("\nВыберите территорию:")
        for i, territory in enumerate(territories, 1):
            images_count = self.db.get_territory_image_count(territory['id'])
            print(f"{i}. {territory['name']} ({images_count} изображений)")

        try:
            choice = int(input("\nНомер территории: "))
            if choice < 1 or choice > len(territories):
                print("Неверный выбор")
                return
        except ValueError:
            print("Введите число")
            return

        territory = territories[choice - 1]

        # Проверяем наличие изображений
        images = self.db.get_territory_images(territory['id'], limit=2)
        if len(images) < 2:
            print(f"\nНедостаточно изображений для анализа")
            print(f"Нужно минимум 2 изображения, сейчас {len(images)}")
            print(f"Получите новое изображение через меню 'Получить спутниковое изображение'")
            return

        # Выбор размера сетки
        print("\nВыберите размер ячейки сетки:")
        print("1. Мелкая сетка (16px) - высокая детализация")
        print("2. Средняя сетка (32px) - оптимально")
        print("3. Крупная сетка (64px) - быстрый анализ")

        try:
            grid_choice = int(input("Ваш выбор: "))
            if grid_choice == 1:
                grid_size = 16
            elif grid_choice == 2:
                grid_size = 32
            elif grid_choice == 3:
                grid_size = 64
            else:
                print("Используется средний размер (32px)")
                grid_size = 32
        except ValueError:
            grid_size = 32

        print(f"\n🔍 Анализ территории: {territory['name']}")
        print(f"   Размер сетки: {grid_size} пикселей")
        print(f"   Новый снимок: {images[0]['capture_date']}")
        print(f"   Старый снимок: {images[1]['capture_date']}")

        # Проверяем файлы
        for i, img in enumerate(images[:2]):
            if not os.path.exists(img['image_path']):
                print(f"✗ Файл не найден: {img['image_path']}")
                return

        # Запускаем анализ через GridAnalyzer
        results = self.grid_analyzer.analyze_territory_with_grid(
            territory_info=territory,
            old_image_path=images[1]['image_path'],
            new_image_path=images[0]['image_path'],
            grid_size=grid_size
        )

        if results and results.get('success', False):
            print(f"\n✅ Анализ завершен успешно!")
            print(f"   Визуализация: {results.get('visualization_path', 'не создана')}")
            print(f"   Тепловая карта: {results.get('heatmap_path', 'не создана')}")
            print(f"   Отчет: {results.get('export_path', 'не создан')}")

            # Предлагаем открыть изображения
            if results.get('grid_image_path') and os.path.exists(results['grid_image_path']):
                open_img = input("\nОткрыть изображение с сеткой? (y/n): ").lower()
                if open_img == 'y':
                    try:
                        import subprocess
                        if sys.platform == "win32":
                            os.startfile(results['grid_image_path'])
                        elif sys.platform == "darwin":
                            subprocess.call(["open", results['grid_image_path']])
                        else:
                            subprocess.call(["xdg-open", results['grid_image_path']])
                    except Exception as e:
                        print(f"Не удалось открыть файл: {e}")
                        print(f"Файл: {results['grid_image_path']}")
        else:
            error_msg = results.get('error', 'Неизвестная ошибка') if results else 'Нет результатов'
            print(f"\n✗ Ошибка анализа: {error_msg}")

    def create_grid_for_image(self):
        """Создание сетки для одного изображения"""
        print("\n" + "=" * 60)
        print("СОЗДАНИЕ КООРДИНАТНОЙ СЕТКИ")
        print("=" * 60)

        # Выбор источника изображения
        print("\nВыберите источник изображения:")
        print("1. Из базы данных (сохраненные территории)")
        print("2. Указать файл вручную")

        try:
            source_choice = int(input("Ваш выбор: "))
        except ValueError:
            print("Неверный выбор")
            return

        image_path = ""
        lat = 0
        lon = 0

        if source_choice == 1:
            # Из базы данных
            territories = self.db.get_all_territories()
            if not territories:
                print("Нет сохраненных территорий")
                return

            print("\nВыберите территорию:")
            for i, territory in enumerate(territories, 1):
                print(f"{i}. {territory['name']}")

            try:
                choice = int(input("\nНомер территории: "))
                if choice < 1 or choice > len(territories):
                    print("Неверный выбор")
                    return
            except ValueError:
                print("Введите число")
                return

            territory = territories[choice - 1]
            lat = territory['latitude']
            lon = territory['longitude']

            # Получаем последнее изображение
            latest_image = self.db.get_latest_image(territory['id'])
            if not latest_image:
                print("Нет изображений для этой территории")
                return

            image_path = latest_image['image_path']

            print(f"\nТерритория: {territory['name']}")
            print(f"Координаты: {lat:.6f}°, {lon:.6f}°")
            print(f"Изображение: {latest_image['capture_date']}")
            print(f"Путь: {image_path}")

        elif source_choice == 2:
            # Ручной ввод
            image_path = input("\nПуть к изображению: ").strip()
            if not os.path.exists(image_path):
                print(f"Файл не существует: {image_path}")
                return

            try:
                lat = float(input("Широта центра: "))
                lon = float(input("Долгота центра: "))
            except ValueError:
                print("Неверный формат координат")
                return
        else:
            print("Неверный выбор")
            return

        # Выбор размера сетки
        print("\nВыберите размер ячейки:")
        print("1. 16px - очень детально (мелкая сетка)")
        print("2. 32px - оптимально (средняя сетка)")
        print("3. 64px - обзорно (крупная сетка)")

        try:
            size_choice = int(input("Ваш выбор: "))
            if size_choice == 1:
                grid_size = 16
            elif size_choice == 2:
                grid_size = 32
            elif size_choice == 3:
                grid_size = 64
            else:
                grid_size = 32
        except ValueError:
            grid_size = 32

        # Выбор размера области
        print("\nВыберите размер области:")
        print("1. 1x1 км - маленькая область")
        print("2. 2x2 км - оптимально")
        print("3. 3x3 км - большая область")

        try:
            area_choice = int(input("Ваш выбор: "))
            if area_choice == 1:
                area_km = 1.0
            elif area_choice == 2:
                area_km = 2.0
            elif area_choice == 3:
                area_km = 3.0
            else:
                area_km = 2.0
        except ValueError:
            area_km = 2.0

        # Создаем сетку
        analyzer = GridAnalyzer(grid_size=grid_size)

        result = analyzer.create_grid_image(
            image_path=image_path,
            lat_center=lat,
            lon_center=lon,
            area_km=area_km
        )

        if result and result.get('success', False):
            print(f"\n✅ Сетка создана успешно!")
            print(f"   Файл: {result.get('grid_image_path')}")

            # Предлагаем открыть
            open_img = input("\nОткрыть изображение с сеткой? (y/n): ").lower()
            if open_img == 'y':
                try:
                    import subprocess
                    grid_path = result.get('grid_image_path', '')
                    if grid_path and os.path.exists(grid_path):
                        if sys.platform == "win32":
                            os.startfile(grid_path)
                        elif sys.platform == "darwin":
                            subprocess.call(["open", grid_path])
                        else:
                            subprocess.call(["xdg-open", grid_path])
                except Exception as e:
                    print(f"Не удалось открыть файл: {e}")
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Нет результатов'
            print(f"\n✗ Ошибка: {error_msg}")

    def compare_images_with_grid(self):
        """Сравнение двух изображений с сеткой"""
        print("\n" + "=" * 60)
        print("СРАВНЕНИЕ ИЗОБРАЖЕНИЙ С СЕТКОЙ")
        print("=" * 60)

        # Ввод путей к изображениям
        print("\nВведите пути к изображениям:")
        image1_path = input("Первое изображение (старое): ").strip()
        image2_path = input("Второе изображение (новое): ").strip()

        if not os.path.exists(image1_path):
            print(f"✗ Файл не существует: {image1_path}")
            return
        if not os.path.exists(image2_path):
            print(f"✗ Файл не существует: {image2_path}")
            return

        # Ввод координат центра
        print("\nВведите координаты центра области:")
        try:
            lat = float(input("Широта: "))
            lon = float(input("Долгота: "))
        except ValueError:
            print("Неверный формат координат")
            return

        # Выбор параметров
        print("\nВыберите размер ячейки сетки:")
        print("1. 16px (детально)")
        print("2. 32px (оптимально)")
        print("3. 64px (быстро)")

        try:
            size_choice = int(input("Ваш выбор: "))
            grid_size = {1: 16, 2: 32, 3: 64}.get(size_choice, 32)
        except ValueError:
            grid_size = 32

        # Анализ
        analyzer = GridAnalyzer(grid_size=grid_size)

        print(f"\n🔍 Сравнение изображений:")
        print(f"   Старое: {image1_path}")
        print(f"   Новое: {image2_path}")
        print(f"   Центр: {lat:.6f}°, {lon:.6f}°")
        print(f"   Сетка: {grid_size}px")

        # Сначала создаем сетку для второго изображения
        grid_result = analyzer.create_grid_image(
            image_path=image2_path,
            lat_center=lat,
            lon_center=lon,
            area_km=2.0
        )

        if not grid_result or not grid_result.get('success', False):
            error_msg = grid_result.get('error', 'Неизвестно') if grid_result else 'Нет результатов'
            print(f"✗ Ошибка создания сетки: {error_msg}")
            return

        # Затем анализируем изменения
        analysis_result = analyzer.analyze_changes_with_grid(
            image1_path=image1_path,
            image2_path=image2_path,
            grid_info=grid_result
        )

        if analysis_result and analysis_result.get('success', False):
            print(f"\n✅ Анализ завершен!")

            # Выводим краткий отчет
            summary = analysis_result.get('analysis_summary', {})
            changed = summary.get('changed_cells', 0)
            total = summary.get('total_cells', 1)

            print(f"\n📊 КРАТКИЕ РЕЗУЛЬТАТЫ:")
            print(f"   Изменено ячеек: {changed}/{total} ({changed / total * 100:.1f}%)")
            print(f"   Среднее изменение: {summary.get('avg_pixel_change', 0):.1f}%")
            print(f"   Структурные изменения: {summary.get('structural_changes', 0)} ячеек")

            # Предлагаем детальный отчет
            detailed = input("\nПоказать детальный отчет? (y/n): ").lower()
            if detailed == 'y':
                analyzer.print_detailed_report(analysis_result)

            # Экспорт
            export = input("\nЭкспортировать результаты в JSON? (y/n): ").lower()
            if export == 'y':
                analyzer.export_results_to_json(analysis_result)
        else:
            error_msg = analysis_result.get('error', 'Неизвестно') if analysis_result else 'Нет результатов'
            print(f"\n✗ Ошибка анализа: {error_msg}")

    def show_grid_example(self):
        """Показывает пример работы с сеткой"""
        print("\n" + "=" * 60)
        print("ПРИМЕР РАБОТЫ С КООРДИНАТНОЙ СЕТКОЙ")
        print("=" * 60)

        print("\n📐 КООРДИНАТНАЯ СЕТКА позволяет:")
        print("   • Точно определять координаты изменений")
        print("   • Анализировать изменения по ячейкам")
        print("   • Фильтровать изменения из-за освещения")
        print("   • Различать типы изменений (цвет, структура, освещение)")

        print("\n🔍 ПРИНЦИП РАБОТЫ:")
        print("   1. Изображение делится на ячейки фиксированного размера")
        print("   2. Для каждой ячейки рассчитываются географические координаты")
        print("   3. Анализируются изменения внутри каждой ячейки")
        print("   4. Определяется тип изменений (освещение, цвет, структура)")

        print("\n🎨 ЦВЕТОВАЯ СХЕМА В ВИЗУАЛИЗАЦИИ:")
        print("   🔴 Красный - структурные изменения (строительство, разрушение)")
        print("   🔵 Голубой - цветовые изменения (растительность, покраска)")
        print("   🟡 Желтый - изменения освещения (тени, время суток)")
        print("   🟢 Зеленый - незначительные изменения")
        print("   🟠 Оранжевый - значительные изменения")

        print("\n📏 РАЗМЕРЫ СЕТКИ:")
        print("   • 16px - высокая детализация, много ячеек, медленно")
        print("   • 32px - оптимальный баланс детализации и скорости")
        print("   • 64px - обзорный анализ, быстро, меньше деталей")

        print("\n📍 КООРДИНАТЫ:")
        print("   • Подписи показывают широту и долготу")
        print("   • Можно точно определить где произошли изменения")
        print("   • Координаты центра каждой ячейки сохраняются в отчете")

        input("\nНажмите Enter чтобы продолжить...")

    # Методы заглушки для остального функционала
    def territories_menu(self):
        """Меню управления территориями"""
        print("\nМеню управления территориями (заглушка)")
        input("Нажмите Enter чтобы продолжить...")

    def get_satellite_image(self):
        """Получение спутникового изображения"""
        print("\nПолучение спутникового изображения (заглушка)")
        input("Нажмите Enter чтобы продолжить...")

    def analysis_menu(self):
        """Меню анализа изображений"""
        print("\nМеню анализа изображений (заглушка)")
        input("Нажмите Enter чтобы продолжить...")

    def monitoring_menu(self):
        """Меню мониторинга"""
        print("\nМеню мониторинга (заглушка)")
        input("Нажмите Enter чтобы продолжить...")

    def settings_menu(self):
        """Меню настроек"""
        print("\nМеню настроек (заглушка)")
        input("Нажмите Enter чтобы продолжить...")

    def run(self):
        """Запуск главного меню"""
        print_header()

        while True:
            print_menu()

            try:
                choice = input("\nВыберите опцию (0-6): ").strip()

                if choice == '0':
                    print("\nВыход из программы. До свидания!")
                    break
                elif choice == '1':
                    self.territories_menu()
                elif choice == '2':
                    self.get_satellite_image()
                elif choice == '3':
                    self.analysis_menu()
                elif choice == '4':
                    self.grid_analysis_menu()
                elif choice == '5':
                    self.monitoring_menu()
                elif choice == '6':
                    self.settings_menu()
                else:
                    print("Неверный выбор. Попробуйте снова.")

            except KeyboardInterrupt:
                print("\nПрограмма прервана пользователем")
                break
            except Exception as e:
                print(f"\nНеожиданная ошибка: {e}")
                import traceback
                traceback.print_exc()


def main():
    """Главная функция"""
    try:
        app = SatelliteMonitorApp()
        app.run()
    except KeyboardInterrupt:
        print("\nВыход")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()