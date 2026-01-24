"""
Главное меню системы мониторинга спутниковых изображений с поддержкой координатной сетки
"""

import sys
import os
import traceback
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
sys.path.append(str(Path(__file__).parent))

# Импортируем необходимые модули
try:
    from database import Database
    from gee_client import GEEClient
    from change_detector import ChangeDetector
    from grid_analyzer import GridAnalyzer
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    print("Убедитесь, что все модули находятся в той же директории:")
    print("1. database.py")
    print("2. gee_client.py")
    print("3. change_detector.py")
    print("4. grid_analyzer.py")
    sys.exit(1)


def print_header():
    """Печать заголовка"""
    print("\n" + "=" * 60)
    print("🎯 СИСТЕМА МОНИТОРИНГА СПУТНИКОВЫХ ИЗОБРАЖЕНИЙ")
    print("        с поддержкой координатной сетки")
    print("=" * 60)


def print_menu():
    """Печать главного меню"""
    print("\n📋 ГЛАВНОЕ МЕНЮ:")
    print("1. 📍 Управление территориями")
    print("2. 🛰️  Получить спутниковое изображение")
    print("3. 🔍 Анализ изображений (обычный)")
    print("4. 📐 Анализ с координатной сеткой")
    print("5. 📊 Мониторинг и детекция изменений")
    print("6. ⚙️  Настройки и информация")
    print("0. 🚪 Выход")


def print_territories_menu():
    """Печать меню управления территориями"""
    print("\n📍 УПРАВЛЕНИЕ ТЕРРИТОРИЯМИ:")
    print("1. ➕ Добавить новую территорию")
    print("2. 👁️  Просмотреть все территории")
    print("3. ✏️  Редактировать территорию")
    print("4. ❌ Удалить территорию")
    print("5. 📸 Просмотреть изображения территории")
    print("0. ↩️  Назад")


def print_analysis_menu():
    """Печать меню анализа изображений"""
    print("\n🔍 АНАЛИЗ ИЗОБРАЖЕНИЙ:")
    print("1. 🖼️  Анализ одного изображения")
    print("2. ↔️  Сравнить два изображения")
    print("0. ↩️  Назад")


def print_grid_menu():
    """Печать меню работы с координатной сеткой"""
    print("\n📐 АНАЛИЗ С КООРДИНАТНОЙ СЕТКОЙ:")
    print("1. 🗺️  Проанализировать территорию с сеткой")
    print("2. 📏 Создать сетку для изображения")
    print("3. 📊 Сравнить два изображения с сеткой")
    print("4. ℹ️  Показать пример сетки")
    print("0. ↩️  Назад")


def print_monitoring_menu():
    """Печать меню мониторинга"""
    print("\n📊 МОНИТОРИНГ:")
    print("1. 🔄 Проверить изменения на территории")
    print("2. 🏃 Запустить мониторинг всех территорий")
    print("3. 📜 Просмотреть историю изменений")
    print("0. ↩️  Назад")


def print_settings_menu():
    """Печать меню настроек"""
    print("\n⚙️  НАСТРОЙКИ:")
    print("1. ℹ️  Информация о системе")
    print("2. 📧 Настройка email уведомлений")
    print("3. 🗑️  Очистить кэш")
    print("0. ↩️  Назад")


class SatelliteMonitorApp:
    def __init__(self):
        """Инициализация приложения"""
        try:
            self.db = Database()
            self.gee_client = GEEClient()
            self.change_detector = ChangeDetector(self.db, self.gee_client)
            self.grid_analyzer = GridAnalyzer()
            print("✅ Система успешно инициализирована!")
        except Exception as e:
            print(f"❌ Ошибка инициализации системы: {e}")
            traceback.print_exc()
            raise

    # ==================== МЕТОДЫ ДЛЯ ТЕРРИТОРИЙ ====================

    def add_territory(self):
        """Добавление новой территории"""
        print("\n" + "=" * 60)
        print("➕ ДОБАВЛЕНИЕ НОВОЙ ТЕРРИТОРИИ")
        print("=" * 60)

        name = input("\n📝 Название территории: ").strip()
        if not name:
            print("❌ Ошибка: Название не может быть пустым")
            return

        try:
            lat = float(input("📍 Широта (например, 55.7558): "))
            lon = float(input("📍 Долгота (например, 37.6173): "))
        except ValueError:
            print("❌ Ошибка: введите числовые значения координат")
            return

        description = input("📄 Описание (необязательно): ").strip()

        territory_id = self.db.add_territory(name, lat, lon, description)
        if territory_id:
            print(f"\n✅ Территория '{name}' добавлена с ID: {territory_id}")
        else:
            print(f"\n❌ Ошибка при добавлении территории")

    def view_territories(self):
        """Просмотр всех территорий"""
        print("\n" + "=" * 60)
        print("👁️  ВСЕ ТЕРРИТОРИИ")
        print("=" * 60)

        territories = self.db.get_all_territories()

        if not territories:
            print("\n📭 Территории не найдены")
            return

        print(f"\n📊 Найдено территорий: {len(territories)}\n")

        for i, territory in enumerate(territories, 1):
            print(f"{i}. {territory['name']}")
            print(f"   📍 Координаты: {territory['latitude']}, {territory['longitude']}")
            if territory['description']:
                print(f"   📄 Описание: {territory['description']}")

            try:
                images = self.db.get_territory_images(territory['id'])
                print(f"   📸 Изображений: {len(images)}")
                if images:
                    latest = max(images, key=lambda x: x.get('capture_date', ''))
                    print(f"   📅 Последний снимок: {latest.get('capture_date', 'неизвестно')}")
            except:
                print(f"   📸 Нет снимков")
            print()

    def edit_territory(self):
        """Редактирование территории"""
        territories = self.db.get_all_territories()

        if not territories:
            print("\n📭 Нет территорий для редактирования")
            return

        print("\n✏️  Выберите территорию для редактирования:")
        for i, territory in enumerate(territories, 1):
            print(f"{i}. {territory['name']}")

        try:
            choice = int(input("\n📝 Номер территории: "))
            if choice < 1 or choice > len(territories):
                print("❌ Неверный выбор")
                return
        except ValueError:
            print("❌ Введите число")
            return

        territory = territories[choice - 1]

        print(f"\n✏️  Редактирование: {territory['name']}")
        print("(оставьте пустым, чтобы не менять)")

        new_name = input(f"📝 Новое название [{territory['name']}]: ").strip()
        new_lat = input(f"📍 Новая широта [{territory['latitude']}]: ").strip()
        new_lon = input(f"📍 Новая долгота [{territory['longitude']}]: ").strip()
        new_desc = input(f"📄 Новое описание [{territory['description'] or 'нет'}]: ").strip()

        updates = {}
        if new_name:
            updates['name'] = new_name
        if new_lat:
            try:
                updates['latitude'] = float(new_lat)
            except ValueError:
                print("❌ Неверный формат широты")
                return
        if new_lon:
            try:
                updates['longitude'] = float(new_lon)
            except ValueError:
                print("❌ Неверный формат долготы")
                return
        if new_desc:
            updates['description'] = new_desc

        if updates:
            success = self.db.update_territory(territory['id'], **updates)
            if success:
                print(f"\n✅ Территория обновлена")
            else:
                print(f"\n❌ Ошибка при обновлении")
        else:
            print(f"\nℹ️  Изменений нет")

    def delete_territory(self):
        """Удаление территории"""
        territories = self.db.get_all_territories()

        if not territories:
            print("\n📭 Нет территорий для удаления")
            return

        print("\n❌ Выберите территорию для удаления:")
        for i, territory in enumerate(territories, 1):
            print(f"{i}. {territory['name']}")

        try:
            choice = int(input("\n📝 Номер территории: "))
            if choice < 1 or choice > len(territories):
                print("❌ Неверный выбор")
                return
        except ValueError:
            print("❌ Введите число")
            return

        territory = territories[choice - 1]

        confirm = input(f"\n⚠️  Вы уверены, что хотите удалить '{territory['name']}'? (y/n): ").lower()
        if confirm == 'y':
            success = self.db.delete_territory(territory['id'])
            if success:
                print(f"\n✅ Территория '{territory['name']}' удалена")
            else:
                print(f"\n❌ Ошибка при удалении")
        else:
            print("\nℹ️  Удаление отменено")

    def view_territory_images(self):
        """Просмотр изображений территории"""
        territories = self.db.get_all_territories()

        if not territories:
            print("\n📭 Нет территорий")
            return

        print("\n👁️  Выберите территорию:")
        for i, territory in enumerate(territories, 1):
            print(f"{i}. {territory['name']}")

        try:
            choice = int(input("\n📝 Номер территории: "))
            if choice < 1 or choice > len(territories):
                print("❌ Неверный выбор")
                return
        except ValueError:
            print("❌ Введите число")
            return

        territory = territories[choice - 1]
        images = self.db.get_territory_images(territory['id'], limit=20)

        print(f"\n📸 Изображения территории: {territory['name']}")
        print("=" * 40)

        if not images:
            print("📭 Изображений не найдено")
            return

        for i, image in enumerate(images, 1):
            print(f"\n{i}. 📅 Дата: {image['capture_date']}")
            print(f"   📁 Путь: {image['image_path']}")
            print(f"   🆔 ID: {image['id']}")
            if image.get('cloud_cover'):
                print(f"   ☁️  Облачность: {image['cloud_cover']}%")
            if image.get('file_size'):
                print(f"   📏 Размер: {image['file_size'] / 1024:.1f} KB")

            # Проверяем существует ли файл
            if os.path.exists(image['image_path']):
                print(f"   ✅ Статус файла: Существует")
            else:
                print(f"   ❌ Статус файла: Отсутствует")

    # ==================== МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ ИЗОБРАЖЕНИЙ ====================

    def get_satellite_image(self):
        """Получение спутникового изображения"""
        print("\n" + "=" * 60)
        print("🛰️  ПОЛУЧЕНИЕ СПУТНИКОВОГО ИЗОБРАЖЕНИЯ")
        print("=" * 60)

        print("\n📍 Выберите источник координат:")
        print("1. 📂 Выбрать из сохраненных территорий")
        print("2. ✏️  Ввести координаты вручную (не сохранять)")
        print("3. 💾 Ввести координаты и сохранить как новую территорию")

        try:
            source_choice = int(input("\n📝 Ваш выбор: "))
        except ValueError:
            print("❌ Ошибка: Введите число")
            return

        territory_id = None
        territory_name = ""

        if source_choice == 1:
            territories = self.db.get_all_territories()
            if not territories:
                print("❌ Ошибка: Нет сохраненных территорий")
                return

            print("\n📍 Выберите территорию:")
            for i, territory in enumerate(territories, 1):
                print(f"{i}. {territory['name']}")

            try:
                choice = int(input("\n📝 Номер территории: "))
                if choice < 1 or choice > len(territories):
                    print("❌ Ошибка: Неверный выбор")
                    return
            except ValueError:
                print("❌ Ошибка: Введите число")
                return

            territory = territories[choice - 1]
            lat, lon = territory['latitude'], territory['longitude']
            territory_id = territory['id']
            territory_name = territory['name']

        elif source_choice == 2:
            try:
                lat = float(input("\n📍 Широта: "))
                lon = float(input("📍 Долгота: "))
                territory_name = f"Ручной ввод ({lat:.4f}, {lon:.4f})"
            except ValueError:
                print("❌ Ошибка: Неверный формат координат")
                return

        elif source_choice == 3:
            try:
                name = input("\n📝 Название новой территории: ").strip()
                if not name:
                    print("❌ Ошибка: Название не может быть пустым")
                    return

                lat = float(input("📍 Широта: "))
                lon = float(input("📍 Долгота: "))
                description = input("📄 Описание (необязательно): ").strip()

                # Сохраняем как новую территорию
                territory_id = self.db.add_territory(name, lat, lon, description)
                territory_name = name
                print(f"✅ Территория '{name}' сохранена с ID: {territory_id}")

            except ValueError:
                print("❌ Ошибка: Неверный формат координат")
                return
        else:
            print("❌ Ошибка: Неверный выбор")
            return

        date_input = input("📅 Дата (YYYY-MM-DD, Enter для сегодня): ").strip()
        date = date_input if date_input else None

        print("\n⏳ Загрузка изображения...")

        # Получаем изображение
        result = self.gee_client.get_satellite_image(lat, lon, date)

        if result and len(result) >= 3 and result[0]:  # Проверяем успешность
            success = result[0]
            path = result[1]
            capture_date = result[2]
            message = result[3] if len(result) > 3 else ""

            if success and path:
                print(f"\n✅ УСПЕХ!")
                print(f"   📍 Территория: {territory_name}")
                print(f"   📁 Файл: {path}")
                print(f"   📅 Дата съемки: {capture_date}")

                # Анализируем изображение
                analysis = self.gee_client.analyze_image(path) if hasattr(self.gee_client, 'analyze_image') else {}

                if analysis and 'error' not in analysis:
                    print(f"   ☁️  Облачность: {analysis.get('cloud_cover', {}).get('percentage', 'N/A'):.1f}%")
                    print(f"   💡 Яркость: {analysis.get('brightness', {}).get('mean', 'N/A'):.1f}")

                # Сохраняем в базу всегда, даже если territory_id = None
                if territory_id is None:
                    # Создаем временную территорию для ручного ввода
                    territory_id = self.db.add_territory(
                        territory_name,
                        lat,
                        lon,
                        "Временная территория (ручной ввод)"
                    )
                    print(f"   📝 Создана временная территория с ID: {territory_id}")

                # Сохраняем изображение в БД
                file_size = os.path.getsize(path) if os.path.exists(path) else None
                cloud_cover = analysis.get('cloud_cover', {}).get('percentage') if analysis and 'error' not in analysis else None

                image_id = self.db.add_image(
                    territory_id, path, capture_date,
                    cloud_cover, file_size
                )
                if image_id:
                    print(f"   💾 Сохранено в БД с ID: {image_id}")

                    # Предлагаем проанализировать изменения если есть предыдущие изображения
                    previous_images = self.db.get_territory_images(territory_id, limit=1)
                    if len(previous_images) > 1:
                        analyze_changes = input("\n🔄 Проверить изменения по сравнению с предыдущим снимком? (y/n): ").lower()
                        if analyze_changes == 'y':
                            self.change_detector.detect_and_save_changes(territory_id)
                    else:
                        print(f"   ℹ️  Это первое изображение для этой территории")
                else:
                    print(f"   ❌ Ошибка сохранения в БД")
            else:
                print(f"\n❌ ОШИБКА: {message}")
        else:
            print(f"\n❌ ОШИБКА при получении изображения")

    # ==================== МЕТОДЫ АНАЛИЗА ИЗОБРАЖЕНИЙ ====================

    def analyze_single_image(self):
        """Анализ одного изображения"""
        print("\n" + "=" * 60)
        print("🔍 АНАЛИЗ ИЗОБРАЖЕНИЯ")
        print("=" * 60)

        image_path = input("\n📁 Путь к изображению: ").strip()

        if not Path(image_path).exists():
            print(f"❌ Ошибка: Файл не существует: {image_path}")
            return

        print("\n⏳ Анализ...")

        if hasattr(self.gee_client, 'analyze_image'):
            analysis = self.gee_client.analyze_image(image_path)
        else:
            print("❌ Метод analyze_image не доступен в gee_client")
            return

        if 'error' in analysis:
            print(f"❌ Ошибка: {analysis['error']}")
        else:
            print(f"\n📊 РЕЗУЛЬТАТЫ:")
            print(f"   📏 Размер: {analysis.get('dimensions', {}).get('width', 'N/A')}x{analysis.get('dimensions', {}).get('height', 'N/A')}")
            print(f"   ☁️  Облачность: {analysis.get('cloud_cover', {}).get('percentage', 'N/A'):.1f}%")
            print(f"   📋 Оценка облачности: {analysis.get('cloud_cover', {}).get('assessment', 'N/A')}")
            print(f"   💡 Яркость: {analysis.get('brightness', {}).get('mean', 'N/A'):.1f}")

            brightness = analysis.get('brightness', {})
            if 'max' in brightness and 'min' in brightness:
                contrast = brightness['max'] - brightness['min']
                print(f"   🎨 Контрастность: {contrast:.1f}")

            print(f"   🔍 Резкость: {analysis.get('sharpness', {}).get('assessment', 'N/A')}")

    def compare_images(self):
        """Сравнение двух изображений"""
        print("\n" + "=" * 60)
        print("🔄 СРАВНЕНИЕ ИЗОБРАЖЕНИЙ")
        print("=" * 60)

        path1 = input("\n📁 Путь к первому изображению: ").strip()
        path2 = input("📁 Путь ко второму изображению: ").strip()

        if not Path(path1).exists() or not Path(path2).exists():
            print("❌ Ошибка: Один или оба файла не существуют")
            return

        print("\n⏳ Сравнение...")

        if hasattr(self.gee_client, 'compare_images'):
            comparison = self.gee_client.compare_images(path1, path2)
        else:
            print("❌ Метод compare_images не доступен в gee_client")
            return

        if 'error' in comparison:
            print(f"❌ Ошибка: {comparison['error']}")
        else:
            print(f"\n📊 РЕЗУЛЬТАТЫ СРАВНЕНИЯ:")
            print(f"   🎯 Измененные пиксели: {comparison.get('changed_pixels', 0):,}")
            print(f"   📊 Всего пикселей: {comparison.get('total_pixels', 0):,}")
            print(f"   📈 Процент изменений: {comparison.get('change_percentage', 0):.2f}%")
            print(f"   🏷️  Уровень изменений: {comparison.get('change_level', 'N/A')}")

    # ==================== МЕТОДЫ МОНИТОРИНГА ====================

    def check_territory_changes(self):
        """Проверка изменений на территории"""
        territories = self.db.get_all_territories()

        if not territories:
            print("\n📭 Нет территорий")
            return

        print("\n📍 Выберите территорию:")
        for i, territory in enumerate(territories, 1):
            # Получаем количество изображений для территории
            images = self.db.get_territory_images(territory['id'])
            print(f"{i}. {territory['name']} ({len(images)} изображений)")

        try:
            choice = int(input("\n📝 Номер территории: "))
            if choice < 1 or choice > len(territories):
                print("❌ Ошибка: Неверный выбор")
                return
        except ValueError:
            print("❌ Ошибка: Введите число")
            return

        territory = territories[choice - 1]

        # Проверяем сколько изображений есть
        images = self.db.get_territory_images(territory['id'])
        print(f"\n🔄 Проверка изменений: {territory['name']}")
        print(f"   📊 Найдено изображений: {len(images)}")

        if len(images) < 2:
            print(f"   ❌ Ошибка: Недостаточно изображений для сравнения")
            print(f"   ℹ️  Нужно минимум 2 изображения, сейчас {len(images)}")
            print(f"   💡 Получите новое изображение через меню 'Получить спутниковое изображение'")
            return

        # Проверяем существование файлов
        for i, img in enumerate(images[:2]):
            if not os.path.exists(img['image_path']):
                print(f"   ❌ Ошибка: Файл не найден: {img['image_path']}")
                print(f"   ℹ️  Возможно файл был удален или перемещен")
                return

        self.change_detector.detect_and_save_changes(territory['id'])

    def run_monitor_all(self):
        """Запуск мониторинга всех территорий"""
        print("\n" + "=" * 60)
        print("🏃 ЗАПУСК МОНИТОРИНГА ВСЕХ ТЕРРИТОРИЙ")
        print("=" * 60)

        territories = self.db.get_all_territories()

        if not territories:
            print("\n📭 Нет активных территорий")
            return

        print(f"\n📊 Найдено территорий: {len(territories)}")

        for territory in territories:
            print(f"\n📍 Территория: {territory['name']}")

            result = self.gee_client.get_satellite_image(
                territory['latitude'], territory['longitude']
            )

            if result and len(result) >= 3 and result[0]:  # Проверяем успешность
                success = result[0]
                path = result[1]
                date = result[2]
                message = result[3] if len(result) > 3 else ""

                if success:
                    print(f"   ✅ Получен снимок от {date}")

                    # Анализируем
                    if hasattr(self.gee_client, 'analyze_image'):
                        analysis = self.gee_client.analyze_image(path)
                        if analysis and 'error' not in analysis:
                            cloud = analysis.get('cloud_cover', {}).get('percentage', 0)
                            print(f"   ☁️  Облачность: {cloud:.1f}%")

                    # Сохраняем в БД
                    file_size = os.path.getsize(path) if os.path.exists(path) else None
                    cloud_cover = analysis.get('cloud_cover', {}).get('percentage') if 'analysis' in locals() and analysis and 'error' not in analysis else None

                    self.db.add_image(
                        territory['id'], path, date,
                        cloud_cover, file_size
                    )

                    # Проверяем изменения
                    self.change_detector.detect_and_save_changes(territory['id'])
                else:
                    print(f"   ❌ Ошибка: {message}")
            else:
                print(f"   ❌ Ошибка при получении изображения")

        print(f"\n✅ Мониторинг завершен")

    def view_change_history(self):
        """Просмотр истории изменений"""
        if hasattr(self.db, 'get_recent_changes'):
            changes = self.db.get_recent_changes(limit=20)
        else:
            print("❌ Метод get_recent_changes не доступен")
            return

        if not changes:
            print("\n📭 Изменений не обнаружено")
            return

        print(f"\n📜 ИСТОРИЯ ИЗМЕНЕНИЙ (последние {len(changes)}):")
        print("=" * 60)

        for change in changes:
            print(f"\n📍 Территория: {change.get('territory_name', 'N/A')}")
            print(f"📅 Обнаружено: {change.get('detected_at', 'N/A')}")
            print(f"📊 Изменения: {change.get('change_percentage', 0):.2f}%")
            print()

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С СЕТКОЙ ====================

    def analyze_with_grid(self):
        """Анализ территории с координатной сеткой"""
        print("\n" + "=" * 60)
        print("📐 АНАЛИЗ С КООРДИНАТНОЙ СЕТКОЙ")
        print("=" * 60)

        # Выбираем территорию
        territories = self.db.get_all_territories()
        if not territories:
            print("\n📭 Нет территорий для анализа")
            print("💡 Сначала добавьте территории через меню 'Управление территориями'")
            return

        print("\n📍 Выберите территорию:")
        for i, territory in enumerate(territories, 1):
            images = self.db.get_territory_images(territory['id'])
            print(f"{i}. {territory['name']} ({len(images)} изображений)")

        try:
            choice = int(input("\n📝 Номер территории: "))
            if choice < 1 or choice > len(territories):
                print("❌ Неверный выбор")
                return
        except ValueError:
            print("❌ Введите число")
            return

        territory = territories[choice - 1]

        # Получаем изображения
        images = self.db.get_territory_images(territory['id'], limit=2)
        if len(images) < 2:
            print(f"\n❌ Недостаточно изображений для анализа")
            print(f"ℹ️  Нужно минимум 2 изображения, сейчас {len(images)}")
            print(f"💡 Получите новое изображение через меню 'Получить спутниковое изображение'")
            return

        new_image = images[0]  # самый новый
        old_image = images[1]  # предыдущий

        # Проверяем существование файлов
        if not os.path.exists(new_image['image_path']):
            print(f"❌ Файл не найден: {new_image['image_path']}")
            return
        if not os.path.exists(old_image['image_path']):
            print(f"❌ Файл не найден: {old_image['image_path']}")
            return

        # Выбор размера сетки
        print("\n📏 Выберите размер ячейки сетки:")
        print("1. 16px - высокая детализация (мелкая сетка)")
        print("2. 32px - оптимально (средняя сетка)")
        print("3. 64px - обзорно (крупная сетка)")

        try:
            grid_choice = int(input("📝 Ваш выбор: "))
            if grid_choice == 1:
                grid_size = 16
            elif grid_choice == 2:
                grid_size = 32
            elif grid_choice == 3:
                grid_size = 64
            else:
                print("ℹ️  Используется средний размер (32px)")
                grid_size = 32
        except ValueError:
            grid_size = 32

        print(f"\n🔍 ПАРАМЕТРЫ АНАЛИЗА:")
        print(f"   📍 Территория: {territory['name']}")
        print(f"   🆕 Новый снимок: {new_image['capture_date']}")
        print(f"   🆖 Старый снимок: {old_image['capture_date']}")
        print(f"   📐 Размер сетки: {grid_size} пикселей")

        # Запускаем анализ через GridAnalyzer
        print(f"\n⏳ Запуск анализа с координатной сеткой...")

        results = self.grid_analyzer.analyze_territory_with_grid(
            territory_info=territory,
            old_image_path=old_image['image_path'],
            new_image_path=new_image['image_path'],
            grid_size=grid_size
        )

        if results and results.get('success', False):
            print(f"\n✅ Анализ завершен успешно!")

            # Выводим основные результаты
            summary = results.get('analysis_summary', {})
            changed_cells = results.get('changed_cells', [])
            total_cells = results.get('total_cells', 0)

            print(f"\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
            print(f"   📊 Всего ячеек: {total_cells}")
            print(f"   🔄 Измененных ячеек: {len(changed_cells)}")
            print(f"   📈 Процент изменений: {len(changed_cells)/total_cells*100:.1f}%")
            print(f"   📊 Среднее изменение: {summary.get('avg_pixel_change', 0):.1f}%")

            # Выводим созданные файлы
            print(f"\n📁 СОЗДАННЫЕ ФАЙЛЫ:")
            if results.get('visualization_path'):
                print(f"   🎨 Визуализация: {results['visualization_path']}")
            if results.get('heatmap_path'):
                print(f"   🗺️  Тепловая карта: {results['heatmap_path']}")
            if results.get('grid_image_path'):
                print(f"   📐 Изображение с сеткой: {results['grid_image_path']}")
            if results.get('export_path'):
                print(f"   💾 JSON отчет: {results['export_path']}")

            # Предлагаем детальный отчет
            detailed = input("\n📊 Показать детальный отчет? (y/n): ").lower()
            if detailed == 'y':
                self.grid_analyzer.print_detailed_report(results)

        else:
            error_msg = results.get('error', 'Неизвестная ошибка') if results else 'Нет результатов'
            print(f"\n❌ Ошибка анализа: {error_msg}")

    def create_grid_for_image(self):
        """Создание сетки для одного изображения"""
        print("\n" + "=" * 60)
        print("📏 СОЗДАНИЕ КООРДИНАТНОЙ СЕТКИ")
        print("=" * 60)

        # Выбор источника изображения
        print("\n📍 Выберите источник изображения:")
        print("1. 📂 Из базы данных (сохраненные территории)")
        print("2. ✏️  Указать файл вручную")

        try:
            source_choice = int(input("📝 Ваш выбор: "))
        except ValueError:
            print("❌ Неверный выбор")
            return

        image_path = ""
        lat = 0
        lon = 0

        if source_choice == 1:
            # Из базы данных
            territories = self.db.get_all_territories()
            if not territories:
                print("❌ Нет сохраненных территорий")
                return

            print("\n📍 Выберите территорию:")
            for i, territory in enumerate(territories, 1):
                print(f"{i}. {territory['name']}")

            try:
                choice = int(input("\n📝 Номер территории: "))
                if choice < 1 or choice > len(territories):
                    print("❌ Неверный выбор")
                    return
            except ValueError:
                print("❌ Введите число")
                return

            territory = territories[choice - 1]
            lat = territory['latitude']
            lon = territory['longitude']

            # Получаем последнее изображение
            images = self.db.get_territory_images(territory['id'], limit=1)
            if not images:
                print(f"❌ Нет изображений для территории {territory['name']}")
                return

            image_path = images[0]['image_path']

            print(f"\n📍 Территория: {territory['name']}")
            print(f"   📍 Координаты: {lat:.6f}°, {lon:.6f}°")
            print(f"   📸 Изображение: {images[0]['capture_date']}")
            print(f"   📁 Путь: {image_path}")

        elif source_choice == 2:
            # Ручной ввод
            image_path = input("\n📁 Путь к изображению: ").strip()
            if not os.path.exists(image_path):
                print(f"❌ Файл не существует: {image_path}")
                return

            try:
                lat = float(input("📍 Широта центра: "))
                lon = float(input("📍 Долгота центра: "))
            except ValueError:
                print("❌ Неверный формат координат")
                return
        else:
            print("❌ Неверный выбор")
            return

        # Выбор размера сетки
        print("\n📏 Выберите размер ячейки:")
        print("1. 16px - очень детально (мелкая сетка)")
        print("2. 32px - оптимально (средняя сетка)")
        print("3. 64px - обзорно (крупная сетка)")

        try:
            size_choice = int(input("📝 Ваш выбор: "))
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
        print("\n🌍 Выберите размер области:")
        print("1. 1x1 км - маленькая область")
        print("2. 2x2 км - оптимально")
        print("3. 3x3 км - большая область")

        try:
            area_choice = int(input("📝 Ваш выбор: "))
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
        print(f"\n⏳ Создание сетки {grid_size}x{grid_size}...")

        result = self.grid_analyzer.create_grid_image(
            image_path=image_path,
            lat_center=lat,
            lon_center=lon,
            area_km=area_km,
            grid_size=grid_size
        )

        if result and result.get('success', False):
            print(f"\n✅ Сетка создана успешно!")
            print(f"   📁 Файл: {result.get('grid_image_path')}")

            # Предлагаем открыть
            open_img = input("\n👁️  Открыть изображение с сеткой? (y/n): ").lower()
            if open_img == 'y':
                try:
                    grid_path = result.get('grid_image_path', '')
                    if grid_path and os.path.exists(grid_path):
                        if sys.platform == "win32":
                            os.startfile(grid_path)
                        elif sys.platform == "darwin":
                            import subprocess
                            subprocess.call(["open", grid_path])
                        else:
                            import subprocess
                            subprocess.call(["xdg-open", grid_path])
                        print("✅ Изображение открыто")
                except Exception as e:
                    print(f"❌ Не удалось открыть файл: {e}")
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Нет результатов'
            print(f"\n❌ Ошибка: {error_msg}")

    def compare_images_with_grid(self):
        """Сравнение двух изображений с сеткой"""
        print("\n" + "=" * 60)
        print("🔄 СРАВНЕНИЕ ИЗОБРАЖЕНИЙ С СЕТКОЙ")
        print("=" * 60)

        # Ввод путей к изображениям
        print("\n📁 Введите пути к изображениям:")
        image1_path = input("Первое изображение (старое): ").strip()
        image2_path = input("Второе изображение (новое): ").strip()

        if not os.path.exists(image1_path):
            print(f"❌ Файл не существует: {image1_path}")
            return
        if not os.path.exists(image2_path):
            print(f"❌ Файл не существует: {image2_path}")
            return

        # Ввод координат центра
        print("\n📍 Введите координаты центра области:")
        try:
            lat = float(input("Широта: "))
            lon = float(input("Долгота: "))
        except ValueError:
            print("❌ Неверный формат координат")
            return

        # Выбор параметров
        print("\n📏 Выберите размер ячейки сетки:")
        print("1. 16px (детально)")
        print("2. 32px (оптимально)")
        print("3. 64px (быстро)")

        try:
            size_choice = int(input("📝 Ваш выбор: "))
            grid_size = {1: 16, 2: 32, 3: 64}.get(size_choice, 32)
        except ValueError:
            grid_size = 32

        print(f"\n🔍 ПАРАМЕТРЫ СРАВНЕНИЯ:")
        print(f"   🆖 Старое: {image1_path}")
        print(f"   🆕 Новое: {image2_path}")
        print(f"   📍 Центр: {lat:.6f}°, {lon:.6f}°")
        print(f"   📐 Сетка: {grid_size}px")

        # Сначала создаем сетку для второго изображения
        print(f"\n⏳ Создание сетки...")
        grid_result = self.grid_analyzer.create_grid_image(
            image_path=image2_path,
            lat_center=lat,
            lon_center=lon,
            area_km=2.0,
            grid_size=grid_size
        )

        if not grid_result or not grid_result.get('success', False):
            error_msg = grid_result.get('error', 'Неизвестно') if grid_result else 'Нет результатов'
            print(f"❌ Ошибка создания сетки: {error_msg}")
            return

        # Затем анализируем изменения
        print(f"\n⏳ Анализ изменений...")
        analysis_result = self.grid_analyzer.analyze_changes_with_grid(
            image1_path=image1_path,
            image2_path=image2_path,
            grid_info=grid_result.get('grid_info', {})
        )

        if analysis_result and analysis_result.get('success', False):
            print(f"\n✅ Анализ завершен!")

            # Выводим краткий отчет
            summary = analysis_result.get('analysis_summary', {})
            changed = summary.get('changed_cells', 0)
            total = summary.get('total_cells', 1)

            print(f"\n📊 КРАТКИЕ РЕЗУЛЬТАТЫ:")
            print(f"   🔄 Изменено ячеек: {changed}/{total} ({changed/total*100:.1f}%)")
            print(f"   📊 Среднее изменение: {summary.get('avg_pixel_change', 0):.1f}%")
            print(f"   🏗️  Структурные изменения: {summary.get('structural_changes', 0)} ячеек")

            # Предлагаем детальный отчет
            detailed = input("\n📊 Показать детальный отчет? (y/n): ").lower()
            if detailed == 'y':
                self.grid_analyzer.print_detailed_report(analysis_result)

            # Экспорт
            export = input("\n💾 Экспортировать результаты в JSON? (y/n): ").lower()
            if export == 'y':
                export_path = self.grid_analyzer.export_results_to_json(analysis_result)
                if export_path:
                    print(f"✅ Результаты экспортированы в: {export_path}")
        else:
            error_msg = analysis_result.get('error', 'Неизвестно') if analysis_result else 'Нет результатов'
            print(f"\n❌ Ошибка анализа: {error_msg}")

    def show_grid_example(self):
        """Показывает пример работы с сеткой"""
        print("\n" + "=" * 60)
        print("ℹ️  ПРИМЕР РАБОТЫ С КООРДИНАТНОЙ СЕТКОЙ")
        print("=" * 60)

        print("\n📐 КООРДИНАТНАЯ СЕТКА позволяет:")
        print("   • 🎯 Точно определять координаты изменений")
        print("   • 📊 Анализировать изменения по ячейкам")
        print("   • ☀️  Фильтровать изменения из-за освещения")
        print("   • 🎨 Различать типы изменений (цвет, структура, освещение)")

        print("\n🔍 ПРИНЦИП РАБОТЫ:")
        print("   1. 🖼️  Изображение делится на ячейки фиксированного размера")
        print("   2. 📍 Для каждой ячейки рассчитываются географические координаты")
        print("   3. 🔍 Анализируются изменения внутри каждой ячейки")
        print("   4. 🏷️  Определяется тип изменений (освещение, цвет, структура)")

        print("\n🎨 ЦВЕТОВАЯ СХЕМА В ВИЗУАЛИЗАЦИИ:")
        print("   🔴 Красный - структурные изменения (строительство, разрушение)")
        print("   🟡 Желтый - цветовые изменения (растительность, покраска)")
        print("   🔵 Синий - изменения освещения (тени, время суток)")
        print("   🟢 Зеленый - незначительные изменения")

        print("\n📏 РАЗМЕРЫ СЕТКИ:")
        print("   • 16px - высокая детализация, много ячеек, медленно")
        print("   • 32px - оптимальный баланс детализации и скорости")
        print("   • 64px - обзорный анализ, быстро, меньше деталей")

        print("\n📍 КООРДИНАТЫ:")
        print("   • 📝 Подписи показывают широту и долготу")
        print("   • 🎯 Можно точно определить где произошли изменения")
        print("   • 💾 Координаты центра каждой ячейки сохраняются в отчете")

        input("\n⏎ Нажмите Enter чтобы продолжить...")

    # ==================== МЕТОДЫ НАСТРОЕК ====================

    def system_info(self):
        """Информация о системе"""
        print("\n" + "=" * 60)
        print("ℹ️  ИНФОРМАЦИЯ О СИСТЕМЕ")
        print("=" * 60)

        try:
            # Статистика из БД
            if hasattr(self.db, 'get_statistics'):
                stats = self.db.get_statistics()
                print(f"\n📊 СТАТИСТИКА:")
                print(f"   📍 Активных территорий: {stats.get('territories', 'N/A')}")
                print(f"   📸 Всего изображений: {stats.get('images', 'N/A')}")
                print(f"   🔄 Обнаружено изменений: {stats.get('changes', 'N/A')}")
                print(f"   📅 Последнее изображение: {stats.get('last_image_date', 'нет')}")
                print(f"   📅 Последнее изменение: {stats.get('last_change_date', 'нет')}")
        except:
            print("\n📊 Статистика временно недоступна")

        try:
            # Информация о кэше
            if hasattr(self.gee_client, 'get_cache_info'):
                cache_info = self.gee_client.get_cache_info()
                print(f"\n🗂️  КЭШ:")
                print(f"   📸 Изображений в кэше: {cache_info.get('image_count', 0)}")
                print(f"   📏 Размер кэша: {cache_info.get('total_size_mb', 0)} MB")
        except:
            print("\n🗂️  Информация о кэше временно недоступна")

        # Информация о email уведомлениях
        print(f"\n📧 EMAIL УВЕДОМЛЕНИЯ:")
        if hasattr(self.change_detector, 'email_config') and self.change_detector.email_config:
            if self.change_detector.email_config.EMAIL_ENABLED:
                print(f"   ✅ Статус: Включены")
                print(f"   📧 Отправитель: {self.change_detector.email_config.EMAIL_FROM}")
                print(f"   📧 Получатель: {self.change_detector.email_config.EMAIL_TO}")
                print(f"   📊 Порог: {self.change_detector.email_config.CHANGE_THRESHOLD}%")
            else:
                print(f"   ❌ Статус: Выключены")
        else:
            print(f"   ⚠️  Статус: Не настроены")

        # Детальная информация о территориях
        territories = self.db.get_all_territories()
        if territories:
            print(f"\n📍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ТЕРРИТОРИЯХ:")
            for territory in territories[:5]:  # Показываем только первые 5
                images = self.db.get_territory_images(territory['id'])
                print(f"   📍 {territory['name']}: {len(images)} изображений")

            if len(territories) > 5:
                print(f"   ... и еще {len(territories) - 5} территорий")

        # Информация о модулях
        print(f"\n🧩 МОДУЛИ:")
        print(f"   🌍 Google Earth Engine: {'✅ Да' if hasattr(self.gee_client, 'ee') else '❌ Нет'}")
        print(f"   🖼️  OpenCV: {'✅ Да' if hasattr(self.gee_client, 'cv2') and self.gee_client.cv2 is not None else '❌ Нет'}")
        print(f"   🎨 Pillow (PIL): ✅ Да")
        print(f"   🌐 Requests: ✅ Да")

    def setup_email_notifications(self):
        """Настройка email уведомлений"""
        print("\n" + "=" * 60)
        print("📧 НАСТРОЙКА EMAIL УВЕДОМЛЕНИЙ")
        print("=" * 60)

        try:
            # Пытаемся импортировать и настроить email
            from config_email import setup_email_notifications
            config = setup_email_notifications()

            # Обновляем детектор изменений с новыми настройками
            self.change_detector = ChangeDetector(self.db, self.gee_client)

            if config.EMAIL_ENABLED:
                print("\n✅ Email уведомления активированы!")
                print(f"   📧 Получатель: {config.EMAIL_TO}")
                print(f"   📊 Порог изменений: {config.CHANGE_THRESHOLD}%")
                print(f"\nℹ️  Теперь при значительных изменениях (> {config.CHANGE_THRESHOLD}%)")
                print(f"   📨 уведомления будут приходить на: {config.EMAIL_TO}")
        except ImportError:
            print("❌ Модуль config_email.py не найден")
            print("💡 Создайте файл config_email.py с настройками email")
        except Exception as e:
            print(f"❌ Ошибка настройки email: {e}")

    def clear_cache(self):
        """Очистка кэша"""
        print("\n" + "=" * 60)
        print("🗑️  ОЧИСТКА КЭША")
        print("=" * 60)

        confirm = input("\n⚠️  ВНИМАНИЕ: Все изображения в кэше будут удалены. Продолжить? (y/n): ").lower()

        if confirm == 'y':
            if hasattr(self.gee_client, 'clear_cache'):
                result = self.gee_client.clear_cache()
                print(f"\n{result}")
            else:
                print("❌ Метод clear_cache не доступен")
        else:
            print("\nℹ️  Очистка отменена")

    # ==================== МЕНЮ ====================

    def territories_menu(self):
        """Меню управления территориями"""
        while True:
            print_territories_menu()
            choice = input("\n📝 Выберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.add_territory()
            elif choice == '2':
                self.view_territories()
            elif choice == '3':
                self.edit_territory()
            elif choice == '4':
                self.delete_territory()
            elif choice == '5':
                self.view_territory_images()
            else:
                print("❌ Неверный выбор")

            input("\n⏎ Нажмите Enter чтобы продолжить...")

    def analysis_menu(self):
        """Меню анализа изображений"""
        while True:
            print_analysis_menu()
            choice = input("\n📝 Выберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.analyze_single_image()
            elif choice == '2':
                self.compare_images()
            else:
                print("❌ Неверный выбор")

            input("\n⏎ Нажмите Enter чтобы продолжить...")

    def grid_analysis_menu(self):
        """Меню анализа с координатной сеткой"""
        while True:
            print_grid_menu()
            choice = input("\n📝 Выберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.analyze_with_grid()
            elif choice == '2':
                self.create_grid_for_image()
            elif choice == '3':
                self.compare_images_with_grid()
            elif choice == '4':
                self.show_grid_example()
            else:
                print("❌ Неверный выбор")

            input("\n⏎ Нажмите Enter чтобы продолжить...")

    def monitoring_menu(self):
        """Меню мониторинга"""
        while True:
            print_monitoring_menu()
            choice = input("\n📝 Выберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.check_territory_changes()
            elif choice == '2':
                self.run_monitor_all()
            elif choice == '3':
                self.view_change_history()
            else:
                print("❌ Неверный выбор")

            input("\n⏎ Нажмите Enter чтобы продолжить...")

    def settings_menu(self):
        """Меню настроек"""
        while True:
            print_settings_menu()
            choice = input("\n📝 Выберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.system_info()
            elif choice == '2':
                self.setup_email_notifications()
            elif choice == '3':
                self.clear_cache()
            else:
                print("❌ Неверный выбор")

            input("\n⏎ Нажмите Enter чтобы продолжить...")

    def run(self):
        """Запуск главного меню"""
        print_header()

        while True:
            print_menu()

            try:
                choice = input("\n📝 Выберите опцию (0-6): ").strip()

                if choice == '0':
                    print("\n🚪 Выход из программы. До свидания!")
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
                    print("❌ Неверный выбор. Попробуйте снова.")

            except KeyboardInterrupt:
                print("\n🛑 Программа прервана пользователем")
                break
            except Exception as e:
                print(f"\n❌ Неожиданная ошибка: {e}")
                traceback.print_exc()
                input("\n⏎ Нажмите Enter чтобы продолжить...")


def main():
    """Главная функция"""
    try:
        app = SatelliteMonitorApp()
        app.run()
    except KeyboardInterrupt:
        print("\n🚪 Выход")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()