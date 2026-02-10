"""меню"""
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime
import shutil


class FileManager:
    def __init__(self, base_path="satellite_images"):
        self.base_path = base_path
        self.folders = {}
        self.setup_folders()

    def get_safe_filename(self, territory_name, timestamp=None):
        """Создать безопасное имя файла только из латинских символов"""
        import re
        from datetime import datetime

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Транслитерация кириллицы в латиницу
        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
            'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
            'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
            'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
            'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
            'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
            'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
            'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
            'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
            ' ': '_', '-': '_'
        }

        # Транслитерируем
        safe_name = ''
        for char in territory_name:
            if char in translit_dict:
                safe_name += translit_dict[char]
            elif char.isalnum():
                safe_name += char
            else:
                safe_name += '_'

        # Убираем пробелы
        safe_name = safe_name.replace(' ', '_').replace('__', '_').strip('_')

        # Если имя пустое, используем territory_номер
        if not safe_name:
            safe_name = f"territory_{hash(territory_name) & 0xFFFFFFFF:08x}"

        return f"satellite_{safe_name}_{timestamp}.jpg"

    def setup_folders(self):
        """Создать постоянные папки (без дат в названиях)"""
        self.folders = {
            'original': os.path.join(self.base_path, "original"),
            'processed': os.path.join(self.base_path, "processed"),
            'analysis': os.path.join(self.base_path, "analysis"),
            'comparison': os.path.join(self.base_path, "comparison"),
            'grid': os.path.join(self.base_path, "grid"),
            'temp': os.path.join(self.base_path, "temp"),
            'changes': os.path.join(self.base_path, "changes"),
            'heatmaps': os.path.join(self.base_path, "heatmaps"),
            'reports': os.path.join(self.base_path, "reports"),
            'exports': os.path.join(self.base_path, "exports"),
            'deleted': os.path.join(self.base_path, "deleted"),
        }

        for name, path in self.folders.items():
            os.makedirs(path, exist_ok=True)

        print(f"Папки созданы в: {self.base_path}")
        return self.folders

    def get_path(self, file_type, territory_name=None, filename=None):
        """Получить путь для сохранения файла"""
        if filename is None and territory_name is not None:
            # Автоматически создаем безопасное имя
            filename = self.get_safe_filename(territory_name)

        if file_type in self.folders:
            return os.path.join(self.folders[file_type], filename)
        else:
            # Если тип не указан, сохраняем в папку по умолчанию
            default_path = os.path.join(self.base_path, "misc")
            os.makedirs(default_path, exist_ok=True)
            return os.path.join(default_path, filename)

    def move_to_deleted(self, file_path, reason=""):
        """Переместить файл в папку удаленных"""
        if not os.path.exists(file_path):
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        reason_suffix = f"_{reason}" if reason else ""
        new_filename = f"deleted_{timestamp}{reason_suffix}_{filename}"

        # Используем постоянную папку deleted, а не с датой
        new_path = os.path.join(self.folders['deleted'], new_filename)

        try:
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.move(file_path, new_path)
            print(f"Файл перемещен в deleted: {new_path}")
            return new_path
        except Exception as e:
            print(f"Ошибка перемещения файла в deleted: {e}")
            return None

    def clean_temp(self):
        """Очистка временных файлов"""
        temp_path = self.folders['temp']
        temp_files = os.listdir(temp_path) if os.path.exists(temp_path) else []
        deleted_count = 0

        for file in temp_files:
            try:
                file_path = os.path.join(temp_path, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                print(f"Ошибка удаления файла {file}: {e}")

        print(f"Удалено временных файлов: {deleted_count}")

    def organize_existing_files(self):
        """Организация существующих файлов в постоянные папки"""
        print("\nПоиск и организация существующих файлов...")

        # Паттерны для поиска файлов
        patterns = {
            'analysis_grid_*.jpg': 'grid',
            'comparison_grid_*.jpg': 'comparison',
            'grid_*.jpg': 'grid',
            'real_changes_*.jpg': 'changes',
            '*.png': 'original',
            '*.jpg': 'original',
            '*.jpeg': 'original'
        }

        moved_count = 0

        for pattern, folder_type in patterns.items():
            # Ищем файлы в текущей директории
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    # Сохраняем оригинальное имя или добавляем timestamp
                    new_name = file_path.name

                    # Получаем путь для сохранения в постоянную папку
                    new_path = os.path.join(self.folders[folder_type], new_name)

                    # Если файл уже существует, добавляем номер
                    counter = 1
                    while os.path.exists(new_path):
                        name, ext = os.path.splitext(new_name)
                        new_path = os.path.join(self.folders[folder_type], f"{name}_{counter}{ext}")
                        counter += 1

                    try:
                        # Перемещаем файл
                        shutil.move(str(file_path), new_path)
                        print(f"{file_path.name} -> {os.path.basename(new_path)}")
                        moved_count += 1
                    except Exception as e:
                        print(f"Ошибка перемещения {file_path.name}: {e}")

        if moved_count > 0:
            print(f"Организовано файлов: {moved_count}")
        else:
            print("Новых файлов для организации не найдено")

    def get_path(self, file_type, filename):
        """Получить путь для сохранения файла по типу"""
        if file_type in self.folders:
            return os.path.join(self.folders[file_type], filename)
        else:
            # Если тип не указан, сохраняем в папку по умолчанию
            default_path = os.path.join(self.base_path, "misc")
            os.makedirs(default_path, exist_ok=True)
            return os.path.join(default_path, filename)

    def move_to_deleted(self, file_path, reason=""):
        """Переместить файл в папку удаленных"""
        if not os.path.exists(file_path):
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        reason_suffix = f"_{reason}" if reason else ""
        new_filename = f"deleted_{timestamp}{reason_suffix}_{filename}"

        # Используем постоянную папку deleted, а не с датой
        new_path = os.path.join(self.folders['deleted'], new_filename)

        try:
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.move(file_path, new_path)
            print(f"Файл перемещен в deleted: {new_path}")
            return new_path
        except Exception as e:
            print(f"Ошибка перемещения файла в deleted: {e}")
            return None

    def clean_temp(self):
        """Очистка временных файлов"""
        temp_path = self.folders['temp']
        temp_files = os.listdir(temp_path) if os.path.exists(temp_path) else []
        deleted_count = 0

        for file in temp_files:
            try:
                file_path = os.path.join(temp_path, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                print(f"Ошибка удаления файла {file}: {e}")

        print(f"Удалено временных файлов: {deleted_count}")

    def organize_existing_files(self):
        """Организация существующих файлов в постоянные папки"""
        print("\nПоиск и организация существующих файлов...")

        # Паттерны для поиска файлов
        patterns = {
            'analysis_grid_*.jpg': 'grid',
            'comparison_grid_*.jpg': 'comparison',
            'grid_*.jpg': 'grid',
            'real_changes_*.jpg': 'changes',
            '*.png': 'original',
            '*.jpg': 'original',
            '*.jpeg': 'original'
        }

        moved_count = 0

        for pattern, folder_type in patterns.items():
            # Ищем файлы в текущей директории
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    new_name = file_path.name
                    new_path = os.path.join(self.folders[folder_type], new_name)
                    # Если файл уже существует, добавляем номер
                    counter = 1
                    while os.path.exists(new_path):
                        name, ext = os.path.splitext(new_name)
                        new_path = os.path.join(self.folders[folder_type], f"{name}_{counter}{ext}")
                        counter += 1

                    try:
                        # Перемещаем файл
                        shutil.move(str(file_path), new_path)
                        print(f"{file_path.name} -> {os.path.basename(new_path)}")
                        moved_count += 1
                    except Exception as e:
                        print(f"Ошибка перемещения {file_path.name}: {e}")

        if moved_count > 0:
            print(f"Организовано файлов: {moved_count}")
        else:
            print("Новых файлов для организации не найдено")


sys.path.append(str(Path(__file__).parent))

try:
    from database import Database
    from gee_client import GEEClient
    from change_detector import ChangeDetector
    from grid_analyzer import GridAnalyzer
except ImportError as e:
    print(f"Ошибка импорта модулей: {e}")
    print("Убедитесь, что все модули находятся в той же директории:")
    print("1. database.py")
    print("2. gee_client.py")
    print("3. change_detector.py")
    print("4. grid_analyzer.py")
    sys.exit(1)


def print_header():
    print("\n" + "=" * 60)
    print("СИСТЕМА МОНИТОРИНГА СПУТНИКОВЫХ ИЗОБРАЖЕНИЙ")
    print("        с поддержкой координатной сетки")
    print("=" * 60)


def print_menu():
    print("\nГЛАВНОЕ МЕНЮ:")
    print("1. Управление территориями")
    print("2. Получить спутниковое изображение")
    print("3. Анализ изображений (обычный)")
    print("4. Анализ с координатной сеткой")
    print("5. Мониторинг и детекция изменений")
    print("6. Настройки и информация")
    print("7. Управление файлами")
    print("0. Выход")


def print_territories_menu():
    print("\nУПРАВЛЕНИЕ ТЕРРИТОРИЯМИ:")
    print("1. Добавить новую территорию")
    print("2. Просмотреть все территории")
    print("3. Редактировать территорию")
    print("4. Удалить территорию")
    print("5. Просмотреть изображения территории")
    print("6. Управление изображениями территории")
    print("0. Назад")


def print_territory_images_menu():
    print("\nУПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ ТЕРРИТОРИИ:")
    print("1. Просмотреть все изображения")
    print("2. Удалить изображение")
    print("3. Удалить несколько изображений")
    print("4. Удалить изображения старше...")
    print("5. Удалить изображения с высокой облачностью")
    print("6. Удалить изображения меньшего размера")
    print("7. Пересчитать статистику территории")
    print("0. Назад")


def print_analysis_menu():
    print("\nАНАЛИЗ ИЗОБРАЖЕНИЙ:")
    print("1. Анализ одного изображения")
    print("2. Сравнить два изображения")
    print("0. Назад")


def print_grid_menu():
    print("\nАНАЛИЗ С КООРДИНАТНОЙ СЕТКОЙ:")
    print("1. Проанализировать территорию с сеткой")
    print("2. Создать сетку для изображения")
    print("3. Сравнить два изображения с сеткой")
    print("4. Показать пример сетки")
    print("0. Назад")


def print_monitoring_menu():
    print("\nМОНИТОРИНГ:")
    print("1. Проверить изменения на территории")
    print("2. Запустить мониторинг всех территорий")
    print("3. Просмотреть историю изменений")
    print("0. Назад")


def print_settings_menu():
    print("\nНАСТРОЙКИ:")
    print("1. Информация о системе")
    print("2. Настройка email уведомлений")
    print("3. Очистить кэш")
    print("0. Назад")


def print_files_menu():
    print("\nУПРАВЛЕНИЕ ФАЙЛАМИ:")
    print("1. Организовать существующие файлы")
    print("2. Показать структуру папок")
    print("3. Очистить временные файлы")
    print("4. Открыть папку с изображениями")
    print("5. Найти и удалить дубликаты изображений")
    print("0. Назад")


class SatelliteMonitorApp:
    def __init__(self):
        try:
            self.file_manager = FileManager()
            self.db = Database()
            self.gee_client = GEEClient()
            self.change_detector = ChangeDetector(self.db, self.gee_client)
            self.grid_analyzer = GridAnalyzer()
            print("Система успешно инициализирована!")
            self.organize_existing_files_option()
        except Exception as e:
            print(f"Ошибка инициализации системы: {e}")
            traceback.print_exc()
            raise

    def add_territory(self):
        print("\n" + "=" * 60)
        print(" ДОБАВЛЕНИЕ НОВОЙ ТЕРРИТОРИИ")
        print("=" * 60)

        name = input("\nНазвание территории: ").strip()
        if not name:
            print("Ошибка: Название не может быть пустым")
            return

        try:
            lat = float(input("Широта (например, 55.7558): "))
            lon = float(input("Долгота (например, 37.6173): "))
        except ValueError:
            print("Ошибка: введите числовые значения координат")
            return

        description = input("Описание (необязательно): ").strip()

        territory_id = self.db.add_territory(name, lat, lon, description)
        if territory_id:
            print(f"\nТерритория '{name}' добавлена с ID: {territory_id}")
        else:
            print(f"\nОшибка при добавлении территории")

    def view_territories(self):
        print("\n" + "=" * 60)
        print("ВСЕ ТЕРРИТОРИИ")
        print("=" * 60)

        territories = self.db.get_all_territories()
        if not territories:
            print("\nТерритории не найдены")
            return

        print(f"\nНайдено территорий: {len(territories)}\n")
        for i, territory in enumerate(territories, 1):
            print(f"{i}. {territory['name']}")
            print(f"   Координаты: {territory['latitude']}, {territory['longitude']}")
            if territory['description']:
                print(f"   Описание: {territory['description']}")
            try:
                images = self.db.get_territory_images(territory['id'])
                print(f"   Изображений: {len(images)}")
                if images:
                    latest = max(images, key=lambda x: x.get('capture_date', ''))
                    print(f"   Последний снимок: {latest.get('capture_date', 'неизвестно')}")
            except:
                print(f"   Нет снимков")
            print()

    def edit_territory(self):
        territories = self.db.get_all_territories()
        if not territories:
            print("\nНет территорий для редактирования")
            return

        print("\nВыберите территорию для редактирования:")
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
        print(f"\nРедактирование: {territory['name']}")
        print("(оставьте пустым, чтобы не менять)")

        new_name = input(f"Новое название [{territory['name']}]: ").strip()
        new_lat = input(f"Новая широта [{territory['latitude']}]: ").strip()
        new_lon = input(f"Новая долгота [{territory['longitude']}]: ").strip()
        new_desc = input(f"Новое описание [{territory['description'] or 'нет'}]: ").strip()

        updates = {}
        if new_name:
            updates['name'] = new_name
        if new_lat:
            try:
                updates['latitude'] = float(new_lat)
            except ValueError:
                print("Неверный формат широты")
                return
        if new_lon:
            try:
                updates['longitude'] = float(new_lon)
            except ValueError:
                print("Неверный формат долготы")
                return
        if new_desc:
            updates['description'] = new_desc

        if updates:
            success = self.db.update_territory(territory['id'], **updates)
            if success:
                print(f"\nТерритория обновлена")
            else:
                print(f"\nОшибка при обновлении")
        else:
            print(f"\nИзменений нет")

    def delete_territory(self):
        territories = self.db.get_all_territories()
        if not territories:
            print("\nНет территорий для удаления")
            return

        print("\nВыберите территорию для удаления:")
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
        confirm = input(f"\nВы уверены, что хотите удалить '{territory['name']}'? (y/n): ").lower()
        if confirm == 'y':
            images = self.db.get_territory_images(territory['id'])
            for image in images:
                self.delete_image_with_confirmation(image, force=True, reason=f"удаление_территории_{territory['id']}")

            success = self.db.delete_territory(territory['id'])
            if success:
                print(f"\nТерритория '{territory['name']}' удалена")
            else:
                print(f"\nОшибка при удалении")
        else:
            print("\nУдаление отменено")

    def view_territory_images(self):
        territories = self.db.get_all_territories()
        if not territories:
            print("\nНет территорий")
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
        images = self.db.get_territory_images(territory['id'], limit=20)
        print(f"\nИзображения территории: {territory['name']}")
        print("=" * 40)

        if not images:
            print("Изображений не найдено")
            return

        for i, image in enumerate(images, 1):
            print(f"\n{i}. Дата: {image['capture_date']}")
            print(f"   Путь: {image['image_path']}")
            print(f"   ID: {image['id']}")
            if image.get('cloud_cover'):
                print(f"   Облачность: {image['cloud_cover']}%")
            if image.get('file_size'):
                print(f"   Размер: {image['file_size'] / 1024:.1f} KB")
            if os.path.exists(image['image_path']):
                print(f"   Статус файла: Существует")
            else:
                print(f"   Статус файла: Отсутствует")

    def manage_territory_images(self):
        territories = self.db.get_all_territories()
        if not territories:
            print("\nНет территорий")
            return

        print("\nВыберите территорию для управления изображениями:")
        for i, territory in enumerate(territories, 1):
            images = self.db.get_territory_images(territory['id'])
            print(f"{i}. {territory['name']} ({len(images)} изображений)")

        try:
            choice = int(input("\nНомер территории: "))
            if choice < 1 or choice > len(territories):
                print("Неверный выбор")
                return
        except ValueError:
            print("Введите число")
            return

        territory = territories[choice - 1]

        while True:
            print(f"\nУПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ: {territory['name']}")
            print_territory_images_menu()

            choice = input("\nВыберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.view_all_territory_images(territory)
            elif choice == '2':
                self.delete_single_image(territory)
            elif choice == '3':
                self.delete_multiple_images(territory)
            elif choice == '4':
                self.delete_old_images(territory)
            elif choice == '5':
                self.delete_cloudy_images(territory)
            elif choice == '6':
                self.delete_small_images(territory)
            elif choice == '7':
                self.recalculate_territory_stats(territory)
            else:
                print("Неверный выбор")

    def view_all_territory_images(self, territory):
        images = self.db.get_territory_images(territory['id'], limit=100)
        if not images:
            print(f"\nНет изображений для территории: {territory['name']}")
            return

        print(f"\nВСЕ ИЗОБРАЖЕНИЯ ТЕРРИТОРИИ: {territory['name']}")
        print("=" * 60)
        print(f"Всего изображений: {len(images)}")

        for i, image in enumerate(images, 1):
            exists = "[+]" if os.path.exists(image['image_path']) else "[-]"
            print(f"\n{i}. {exists} ID: {image['id']}")
            print(f"   Дата: {image['capture_date']}")
            print(f"   Путь: {image['image_path']}")
            if image.get('cloud_cover'):
                cloud_info = f"Облачность: {image['cloud_cover']}%"
                print(f"   {cloud_info}")
            if image.get('file_size'):
                size_kb = image['file_size'] / 1024
                print(f"   Размер: {size_kb:.1f} KB")

            if i > 1 and image.get('file_size') and images[i - 2].get('file_size'):
                if abs(image['file_size'] - images[i - 2]['file_size']) < 100:
                    print(f"   Возможный дубликат предыдущего изображения")

    def delete_single_image(self, territory):
        images = self.db.get_territory_images(territory['id'])
        if not images:
            print(f"\nНет изображений для удаления")
            return

        print(f"\nУДАЛЕНИЕ ИЗОБРАЖЕНИЯ: {territory['name']}")
        print("=" * 40)

        for i, image in enumerate(images[:10], 1):
            exists = "[+]" if os.path.exists(image['image_path']) else "[-]"
            cloud_info = f", Облачность: {image.get('cloud_cover', 'N/A')}%" if image.get('cloud_cover') else ""
            print(f"{i}. {exists} {image['capture_date']}{cloud_info}")

        try:
            choice = int(input("\nНомер изображения для удаления: "))
            if choice < 1 or choice > len(images):
                print("Неверный выбор")
                return
        except ValueError:
            print("Введите число")
            return

        image = images[choice - 1]
        self.delete_image_with_confirmation(image)

    def delete_multiple_images(self, territory):
        images = self.db.get_territory_images(territory['id'])
        if not images:
            print(f"\nНет изображений для удаления")
            return

        print(f"\nУДАЛЕНИЕ НЕСКОЛЬКИХ ИЗОБРАЖЕНИЙ: {territory['name']}")
        print("=" * 50)

        for i, image in enumerate(images, 1):
            exists = "[+]" if os.path.exists(image['image_path']) else "[-]"
            cloud_info = f", Облачность: {image.get('cloud_cover', 'N/A')}%" if image.get('cloud_cover') else ""
            print(f"{i}. {exists} {image['capture_date']}{cloud_info}")

        print("\nВведите номера изображений для удаления (через запятую или диапазон, например: 1,3,5-7)")
        print("   Или 'all' для удаления всех изображений")

        selection = input("Ваш выбор: ").strip().lower()

        if selection == 'all':
            confirm = input(f"\nВы уверены, что хотите удалить ВСЕ {len(images)} изображений? (y/n): ").lower()
            if confirm == 'y':
                deleted_count = 0
                for image in images:
                    if self.delete_image_with_confirmation(image, force=True, reason="удаление_всех"):
                        deleted_count += 1
                print(f"\nУдалено изображений: {deleted_count}/{len(images)}")
            return

        selected_indices = set()
        parts = selection.split(',')

        for part in parts:
            part = part.strip()
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    selected_indices.update(range(start, end + 1))
                except ValueError:
                    print(f"Неверный диапазон: {part}")
                    return
            else:
                try:
                    selected_indices.add(int(part))
                except ValueError:
                    print(f"Неверный номер: {part}")
                    return

        valid_indices = [i for i in selected_indices if 1 <= i <= len(images)]

        if not valid_indices:
            print("Нет допустимых номеров для удаления")
            return

        print(f"\nБудут удалены следующие изображения:")
        for idx in sorted(valid_indices):
            image = images[idx - 1]
            print(f"   {idx}. {image['capture_date']} ({image['image_path']})")

        confirm = input(f"\nУдалить {len(valid_indices)} изображений? (y/n): ").lower()
        if confirm == 'y':
            deleted_count = 0
            for idx in sorted(valid_indices, reverse=True):
                image = images[idx - 1]
                if self.delete_image_with_confirmation(image, force=True, reason="множественное_удаление"):
                    deleted_count += 1
            print(f"\nУдалено изображений: {deleted_count}/{len(valid_indices)}")

    def delete_old_images(self, territory):
        images = self.db.get_territory_images(territory['id'])
        if not images:
            print(f"\nНет изображений для удаления")
            return

        print(f"\nУДАЛЕНИЕ СТАРЫХ ИЗОБРАЖЕНИЙ: {territory['name']}")
        print("=" * 50)

        images_sorted = sorted(images, key=lambda x: x.get('capture_date', ''), reverse=True)

        print("Доступные даты изображений:")
        dates = set(img['capture_date'] for img in images_sorted if img.get('capture_date'))
        for i, date in enumerate(sorted(dates, reverse=True)[:10], 1):
            count = sum(1 for img in images_sorted if img.get('capture_date') == date)
            print(f"   {i}. {date} ({count} изображений)")

        print("\nВыберите опцию:")
        print("1. Удалить изображения старше определенной даты")
        print("2. Оставить только последние N изображений")

        try:
            option = int(input("Ваш выбор: "))
        except ValueError:
            print("Неверный выбор")
            return

        if option == 1:
            date_cutoff = input("Введите дату (YYYY-MM-DD), старше которой удалять: ").strip()
            try:
                datetime.strptime(date_cutoff, "%Y-%m-%d")
            except ValueError:
                print("Неверный формат даты. Используйте YYYY-MM-DD")
                return

            old_images = [img for img in images if img.get('capture_date', '') < date_cutoff]

            if not old_images:
                print(f"\nНет изображений старше {date_cutoff}")
                return

            print(f"\nНайдено {len(old_images)} изображений старше {date_cutoff}:")
            for img in old_images[:5]:
                print(f"   • {img['capture_date']}")
            if len(old_images) > 5:
                print(f"   ... и еще {len(old_images) - 5} изображений")

        elif option == 2:
            try:
                keep_count = int(input("Сколько последних изображений оставить? "))
                if keep_count < 1:
                    print("Число должно быть положительным")
                    return

                if keep_count >= len(images):
                    print(f"Все изображения будут сохранены (оставить {keep_count} из {len(images)})")
                    return

                old_images = images_sorted[keep_count:]

                print(f"\nБудут удалены {len(old_images)} самых старых изображений:")
                for img in old_images[:5]:
                    print(f"   • {img['capture_date']}")
                if len(old_images) > 5:
                    print(f"   ... и еще {len(old_images) - 5} изображений")

            except ValueError:
                print("Введите число")
                return
        else:
            print("Неверный выбор")
            return

        if 'old_images' in locals() and old_images:
            confirm = input(f"\nУдалить {len(old_images)} изображений? (y/n): ").lower()
            if confirm == 'y':
                deleted_count = 0
                for image in old_images:
                    if self.delete_image_with_confirmation(image, force=True, reason="удаление_старых"):
                        deleted_count += 1
                print(f"\nУдалено старых изображений: {deleted_count}/{len(old_images)}")

    def delete_cloudy_images(self, territory):
        images = self.db.get_territory_images(territory['id'])
        if not images:
            print(f"\nНет изображений для удаления")
            return

        cloudy_images = [img for img in images if img.get('cloud_cover') is not None]

        if not cloudy_images:
            print(f"\nНет изображений с информацией об облачности")
            return

        print(f"\nУДАЛЕНИЕ ОБЛАЧНЫХ ИЗОБРАЖЕНИЙ: {territory['name']}")
        print("=" * 50)

        cloud_levels = {}
        for img in cloudy_images:
            cloud = img['cloud_cover']
            level = "очень облачно" if cloud > 70 else "облачно" if cloud > 40 else "малооблачно"
            cloud_levels.setdefault(level, []).append(img)

        print("Распределение по облачности:")
        for level, imgs in cloud_levels.items():
            avg_cloud = sum(img['cloud_cover'] for img in imgs) / len(imgs)
            print(f"   • {level.capitalize()}: {len(imgs)} изображений, среднее: {avg_cloud:.1f}%")

        try:
            threshold = float(input("\nВведите порог облачности для удаления (например, 50 для >50%): "))
            if threshold < 0 or threshold > 100:
                print("Порог должен быть от 0 до 100%")
                return
        except ValueError:
            print("Введите число")
            return

        images_to_delete = [img for img in cloudy_images if img['cloud_cover'] > threshold]

        if not images_to_delete:
            print(f"\nНет изображений с облачностью выше {threshold}%")
            return

        print(f"\nНайдено {len(images_to_delete)} изображений с облачностью > {threshold}%:")
        for img in images_to_delete[:5]:
            print(f"   • {img['capture_date']}: {img['cloud_cover']}%")
        if len(images_to_delete) > 5:
            print(f"   ... и еще {len(images_to_delete) - 5} изображений")

        confirm = input(f"\nУдалить {len(images_to_delete)} облачных изображений? (y/n): ").lower()
        if confirm == 'y':
            deleted_count = 0
            for image in images_to_delete:
                if self.delete_image_with_confirmation(image, force=True,
                                                       reason=f"высокая_облачность_{image['cloud_cover']}%"):
                    deleted_count += 1
            print(f"\nУдалено облачных изображений: {deleted_count}/{len(images_to_delete)}")

    def delete_small_images(self, territory):
        images = self.db.get_territory_images(territory['id'])
        if not images:
            print(f"\nНет изображений для удаления")
            return

        sized_images = [img for img in images if img.get('file_size') is not None]

        if not sized_images:
            print(f"\nНет изображений с информацией о размере")
            return

        print(f"\nУДАЛЕНИЕ МАЛЕНЬКИХ ИЗОБРАЖЕНИЙ: {territory['name']}")
        print("=" * 50)

        sizes = [img['file_size'] for img in sized_images]
        avg_size = sum(sizes) / len(sizes)
        min_size = min(sizes)
        max_size = max(sizes)

        print(f"Статистика размеров:")
        print(f"   • Средний размер: {avg_size / 1024:.1f} KB")
        print(f"   • Минимальный размер: {min_size / 1024:.1f} KB")
        print(f"   • Максимальный размер: {max_size / 1024:.1f} KB")

        try:
            threshold_kb = float(input("\nВведите порог размера в KB (меньше которого удалять): "))
            threshold_bytes = threshold_kb * 1024
        except ValueError:
            print("Введите число")
            return

        small_images = [img for img in sized_images if img['file_size'] < threshold_bytes]

        if not small_images:
            print(f"\nНет изображений размером меньше {threshold_kb:.1f} KB")
            return

        print(f"\nНайдено {len(small_images)} изображений размером < {threshold_kb:.1f} KB:")
        for img in small_images[:5]:
            size_kb = img['file_size'] / 1024
            print(f"   • {img['capture_date']}: {size_kb:.1f} KB")
        if len(small_images) > 5:
            print(f"   ... и еще {len(small_images) - 5} изображений")

        confirm = input(f"\nУдалить {len(small_images)} маленьких изображений? (y/n): ").lower()
        if confirm == 'y':
            deleted_count = 0
            for image in small_images:
                if self.delete_image_with_confirmation(image, force=True,
                                                       reason=f"маленький_размер_{image['file_size'] / 1024:.1f}kb"):
                    deleted_count += 1
            print(f"\nУдалено маленьких изображений: {deleted_count}/{len(small_images)}")

    def recalculate_territory_stats(self, territory):
        print(f"\nПЕРЕСЧЕТ СТАТИСТИКИ: {territory['name']}")
        print("=" * 50)

        images = self.db.get_territory_images(territory['id'])

        if not images:
            print("Нет изображений для анализа")
            return

        print(f"Анализ {len(images)} изображений...")

        existing_count = 0
        missing_count = 0
        total_size = 0

        for image in images:
            if os.path.exists(image['image_path']):
                existing_count += 1
                try:
                    file_size = os.path.getsize(image['image_path'])
                    total_size += file_size
                    if image.get('file_size') != file_size:
                        self.db.update_image_size(image['id'], file_size)
                        print(f"   Обновлен размер для {image['capture_date']}")
                except Exception as e:
                    print(f"   Ошибка проверки размера {image['capture_date']}: {e}")
            else:
                missing_count += 1
                print(f"   Файл отсутствует: {image['capture_date']}")

        avg_size = total_size / existing_count if existing_count > 0 else 0

        print(f"\nРЕЗУЛЬТАТЫ ПЕРЕСЧЕТА:")
        print(f"   Существует файлов: {existing_count}")
        print(f"   Отсутствует файлов: {missing_count}")
        print(f"   Общий размер: {total_size / 1024 / 1024:.2f} MB")
        print(f"   Средний размер: {avg_size / 1024:.1f} KB")

        if missing_count > 0:
            delete_missing = input(f"\nУдалить из БД {missing_count} отсутствующих файлов? (y/n): ").lower()
            if delete_missing == 'y':
                deleted_count = 0
                for image in images:
                    if not os.path.exists(image['image_path']):
                        if self.db.delete_image(image['id']):
                            deleted_count += 1
                            print(f"   Удален из БД: {image['capture_date']}")
                print(f"\nУдалено записей из БД: {deleted_count}")

    def delete_image_with_confirmation(self, image, force=False, reason=""):
        if not force:
            print(f"\nВЫ УДАЛЯЕТЕ ИЗОБРАЖЕНИЕ:")
            print(f"   Дата: {image.get('capture_date', 'неизвестно')}")
            print(f"   Файл: {image.get('image_path', 'неизвестно')}")
            if image.get('cloud_cover'):
                print(f"   Облачность: {image.get('cloud_cover')}%")

            confirm = input("\nВы уверены, что хотите удалить это изображение? (y/n): ").lower()
            if confirm != 'y':
                print("Удаление отменено")
                return False

        file_path = image.get('image_path')
        moved_to = None

        if file_path and os.path.exists(file_path):
            moved_to = self.file_manager.move_to_deleted(file_path, reason)

        try:
            success = self.db.delete_image(image['id'])
            if success:
                print(f"Изображение удалено из базы данных (ID: {image['id']})")
                if moved_to:
                    print(f"Файл сохранен в: {moved_to}")
                return True
            else:
                print(f"Ошибка удаления изображения из базы данных")
                return False
        except Exception as e:
            print(f"Ошибка при удалении: {e}")
            return False

    def find_and_delete_duplicates(self):
        print("\n" + "=" * 60)
        print("ПОИСК И УДАЛЕНИЕ ДУБЛИКАТОВ ИЗОБРАЖЕНИЙ")
        print("=" * 60)

        territories = self.db.get_all_territories()

        if not territories:
            print("\nНет территорий")
            return

        print("\nПоиск дубликатов...")

        all_duplicates = []

        for territory in territories:
            images = self.db.get_territory_images(territory['id'])

            if len(images) < 2:
                continue

            size_groups = {}
            for image in images:
                if image.get('file_size'):
                    size_groups.setdefault(image['file_size'], []).append(image)

            for size, group in size_groups.items():
                if len(group) > 1:
                    all_duplicates.append({
                        'territory': territory,
                        'size': size,
                        'images': group
                    })

        if not all_duplicates:
            print("\nДубликаты не найдены")
            return

        print(f"\nНайдено групп дубликатов: {len(all_duplicates)}")
        total_duplicates = sum(len(group['images']) for group in all_duplicates)
        print(f"Всего потенциальных дубликатов: {total_duplicates}")

        for i, group in enumerate(all_duplicates[:5], 1):
            territory = group['territory']
            size_kb = group['size'] / 1024
            count = len(group['images'])

            print(f"\n{i}. {territory['name']}:")
            print(f"   Размер файлов: {size_kb:.1f} KB")
            print(f"   Количество дубликатов: {count}")
            print(f"   Даты изображений:")
            for img in group['images'][:3]:
                print(f"      • {img.get('capture_date', 'неизвестно')}")
            if count > 3:
                print(f"      ... и еще {count - 3}")

        if len(all_duplicates) > 5:
            print(f"\n... и еще {len(all_duplicates) - 5} групп дубликатов")

        print("\nВыберите действие:")
        print("1. Удалить все дубликаты (оставить самый новый)")
        print("2. Просмотреть детально каждую группу")
        print("3. Автоматическая очистка дубликатов")

        try:
            choice = int(input("Ваш выбор: "))
        except ValueError:
            print("Неверный выбор")
            return

        if choice == 1:
            self.delete_all_duplicates(all_duplicates)
        elif choice == 2:
            self.review_duplicates_detail(all_duplicates)
        elif choice == 3:
            self.auto_clean_duplicates(all_duplicates)
        else:
            print("Неверный выбор")

    def delete_all_duplicates(self, duplicates):
        total_deleted = 0

        for group in duplicates:
            territory = group['territory']
            images = group['images']

            sorted_images = sorted(images, key=lambda x: x.get('capture_date', ''), reverse=True)
            keep_image = sorted_images[0]
            delete_images = sorted_images[1:]

            print(f"\n{territory['name']}:")
            print(f"   Сохраняем: {keep_image.get('capture_date', 'неизвестно')}")

            for image in delete_images:
                if self.delete_image_with_confirmation(image, force=True, reason="дубликат"):
                    total_deleted += 1

        print(f"\nУдалено дубликатов: {total_deleted}")

    def review_duplicates_detail(self, duplicates):
        for group in duplicates:
            territory = group['territory']
            images = group['images']

            print(f"\n{'=' * 60}")
            print(f"ТЕРРИТОРИЯ: {territory['name']}")
            print(f"ДУБЛИКАТОВ: {len(images)}")
            print(f"{'=' * 60}")

            for i, image in enumerate(images, 1):
                exists = "[+]" if os.path.exists(image['image_path']) else "[-]"
                cloud_info = f", Облачность: {image.get('cloud_cover', 'N/A')}%" if image.get('cloud_cover') else ""
                print(f"{i}. {exists} {image.get('capture_date', 'неизвестно')}{cloud_info}")
                print(f"   {image.get('image_path', 'неизвестно')}")

            print("\nВыберите действие:")
            print("1. Оставить все (пропустить)")
            print("2. Удалить все дубликаты")
            print("3. Выбрать какие удалить")

            try:
                choice = int(input("Ваш выбор: "))
            except ValueError:
                print("Неверный выбор, пропускаем...")
                continue

            if choice == 1:
                print("Пропускаем...")
                continue
            elif choice == 2:
                sorted_images = sorted(images, key=lambda x: x.get('capture_date', ''), reverse=True)
                keep_image = sorted_images[0]
                delete_images = sorted_images[1:]

                print(f"Сохраняем: {keep_image.get('capture_date', 'неизвестно')}")

                deleted_count = 0
                for image in delete_images:
                    if self.delete_image_with_confirmation(image, force=True, reason="дубликат"):
                        deleted_count += 1

                print(f"Удалено: {deleted_count}")
            elif choice == 3:
                print("\nВведите номера изображений для удаления (через запятую):")
                selection = input("Ваш выбор: ").strip()

                try:
                    indices = [int(idx.strip()) for idx in selection.split(',') if idx.strip().isdigit()]
                    valid_indices = [i for i in indices if 1 <= i <= len(images)]

                    if not valid_indices:
                        print("Нет допустимых номеров")
                        continue

                    print(f"\nБудут удалены следующие изображения:")
                    for idx in valid_indices:
                        image = images[idx - 1]
                        print(f"   {idx}. {image.get('capture_date', 'неизвестно')}")

                    confirm = input(f"\nУдалить {len(valid_indices)} изображений? (y/n): ").lower()
                    if confirm == 'y':
                        deleted_count = 0
                        for idx in sorted(valid_indices, reverse=True):
                            image = images[idx - 1]
                            if self.delete_image_with_confirmation(image, force=True, reason="выбранный_дубликат"):
                                deleted_count += 1
                        print(f"Удалено: {deleted_count}")
                except Exception as e:
                    print(f"Ошибка: {e}")

    def auto_clean_duplicates(self, duplicates):
        print("\nАВТОМАТИЧЕСКАЯ ОЧИСТКА ДУБЛИКАТОВ")
        print("=" * 40)

        total_deleted = 0
        criteria = {
            'облачность': 0,
            'дата': 0,
            'размер_файла': 0
        }

        for group in duplicates:
            territory = group['territory']
            images = group['images']

            if len(images) < 2:
                continue

            if all(img.get('cloud_cover') is not None for img in images):
                best_image = min(images, key=lambda x: x['cloud_cover'])
                delete_images = [img for img in images if img['id'] != best_image['id']]
                criteria['облачность'] += len(delete_images)
            else:
                best_image = max(images, key=lambda x: x.get('capture_date', ''))
                delete_images = [img for img in images if img['id'] != best_image['id']]
                criteria['дата'] += len(delete_images)

            for image in delete_images:
                if self.delete_image_with_confirmation(image, force=True, reason="автоочистка_дубликатов"):
                    total_deleted += 1

        print(f"\nРЕЗУЛЬТАТЫ АВТООЧИСТКИ:")
        print(f"   Удалено дубликатов: {total_deleted}")
        print(f"\nКРИТЕРИИ ОТБОРА:")
        for criterion, count in criteria.items():
            if count > 0:
                print(f"   • {criterion}: {count} изображений")

    def get_satellite_image(self):
        print("\n" + "=" * 60)
        print("ПОЛУЧЕНИЕ СПУТНИКОВОГО ИЗОБРАЖЕНИЯ")
        print("=" * 60)

        print("\nВыберите источник координат:")
        print("1. Выбрать из сохраненных территорий")
        print("2. Ввести координаты вручную (не сохранять)")
        print("3. Ввести координаты и сохранить как новую территорию")

        try:
            source_choice = int(input("\nВаш выбор: "))
        except ValueError:
            print("Ошибка: Введите число")
            return

        territory_id = None
        territory_name = ""

        if source_choice == 1:
            territories = self.db.get_all_territories()
            if not territories:
                print("Ошибка: Нет сохраненных территорий")
                return

            print("\nВыберите территорию:")
            for i, territory in enumerate(territories, 1):
                print(f"{i}. {territory['name']}")

            try:
                choice = int(input("\nНомер территории: "))
                if choice < 1 or choice > len(territories):
                    print("Ошибка: Неверный выбор")
                    return
            except ValueError:
                print("Ошибка: Введите число")
                return

            territory = territories[choice - 1]
            lat, lon = territory['latitude'], territory['longitude']
            territory_id = territory['id']
            territory_name = territory['name']

        elif source_choice == 2:
            try:
                lat = float(input("\nШирота: "))
                lon = float(input("Долгота: "))
                territory_name = f"Ручной ввод ({lat:.4f}, {lon:.4f})"
            except ValueError:
                print("Ошибка: Неверный формат координат")
                return

        elif source_choice == 3:
            try:
                name = input("\nНазвание новой территории: ").strip()
                if not name:
                    print("Ошибка: Название не может быть пустым")
                    return

                lat = float(input("Широта: "))
                lon = float(input("Долгота: "))
                description = input("Описание (необязательно): ").strip()

                territory_id = self.db.add_territory(name, lat, lon, description)
                territory_name = name
                print(f"Территория '{name}' сохранена с ID: {territory_id}")

            except ValueError:
                print("Ошибка: Неверный формат координат")
                return
        else:
            print("Ошибка: Неверный выбор")
            return

        date_input = input("Дата (YYYY-MM-DD, Enter для сегодня): ").strip()
        date = date_input if date_input else None

        print("\nЗагрузка изображения...")
        result = self.gee_client.get_satellite_image(lat, lon, date)

        if result and len(result) >= 3 and result[0]:
            success = result[0]
            path = result[1]
            capture_date = result[2]
            message = result[3] if len(result) > 3 else ""

            if success and path:
                new_filename = self.file_manager.get_safe_filename(territory_name)
                new_path = os.path.join(self.file_manager.folders['original'], new_filename)

                try:
                    shutil.move(path, new_path)
                    path = new_path
                    print(f"Изображение сохранено в: {new_path}")
                except Exception as e:
                    print(f"Не удалось переместить файл: {e}")

                print(f"\nУСПЕХ!")
                print(f"   Территория: {territory_name}")
                print(f"   Файл: {path}")
                print(f"   Дата съемки: {capture_date}")

                analysis = self.gee_client.analyze_image(path) if hasattr(self.gee_client, 'analyze_image') else {}

                if analysis and 'error' not in analysis:
                    print(f"   Облачность: {analysis.get('cloud_cover', {}).get('percentage', 'N/A'):.1f}%")
                    print(f"   Яркость: {analysis.get('brightness', {}).get('mean', 'N/A'):.1f}")

                if territory_id is None:
                    territory_id = self.db.add_territory(
                        territory_name,
                        lat,
                        lon,
                        "Временная территория (ручной ввод)"
                    )
                    print(f"   Создана временная территория с ID: {territory_id}")

                file_size = os.path.getsize(path) if os.path.exists(path) else None
                cloud_cover = analysis.get('cloud_cover', {}).get(
                    'percentage') if analysis and 'error' not in analysis else None

                image_id = self.db.add_image(
                    territory_id, path, capture_date,
                    cloud_cover, file_size
                )
                if image_id:
                    print(f"   Сохранено в БД с ID: {image_id}")

                    previous_images = self.db.get_territory_images(territory_id, limit=1)
                    if len(previous_images) > 1:
                        analyze_changes = input(
                            "\nПроверить изменения по сравнению с предыдущим снимком? (y/n): ").lower()
                        if analyze_changes == 'y':
                            self.change_detector.detect_and_save_changes(territory_id)
                    else:
                        print(f"   Это первое изображение для этой территории")
                else:
                    print(f"   Ошибка сохранения в БД")
            else:
                print(f"\nОШИБКА: {message}")
        else:
            print(f"\nОШИБКА при получении изображения")

    def analyze_single_image(self):
        print("\n" + "=" * 60)
        print("АНАЛИЗ ИЗОБРАЖЕНИЯ")
        print("=" * 60)

        image_path = input("\nПуть к изображению: ").strip()

        if not Path(image_path).exists():
            print(f"Ошибка: Файл не существует: {image_path}")
            return

        print("\nАнализ...")

        if hasattr(self.gee_client, 'analyze_image'):
            analysis = self.gee_client.analyze_image(image_path)
        else:
            print("Метод analyze_image не доступен в gee_client")
            return

        if 'error' in analysis:
            print(f"Ошибка: {analysis['error']}")
        else:
            print(f"\nРЕЗУЛЬТАТЫ:")
            print(
                f"   Размер: {analysis.get('dimensions', {}).get('width', 'N/A')}x{analysis.get('dimensions', {}).get('height', 'N/A')}")
            print(f"   Облачность: {analysis.get('cloud_cover', {}).get('percentage', 'N/A'):.1f}%")
            print(f"   Оценка облачности: {analysis.get('cloud_cover', {}).get('assessment', 'N/A')}")
            print(f"   Яркость: {analysis.get('brightness', {}).get('mean', 'N/A'):.1f}")

            brightness = analysis.get('brightness', {})
            if 'max' in brightness and 'min' in brightness:
                contrast = brightness['max'] - brightness['min']
                print(f"   Контрастность: {contrast:.1f}")

            print(f"   Резкость: {analysis.get('sharpness', {}).get('assessment', 'N/A')}")

    def compare_images(self):
        print("\n" + "=" * 60)
        print("СРАВНЕНИЕ ИЗОБРАЖЕНИЙ")
        print("=" * 60)

        path1 = input("\nПуть к первому изображению: ").strip()
        path2 = input("Путь ко второму изображению: ").strip()

        if not Path(path1).exists() or not Path(path2).exists():
            print("Ошибка: Один или оба файла не существуют")
            return

        print("\nСравнение...")

        if hasattr(self.gee_client, 'compare_images'):
            comparison = self.gee_client.compare_images(path1, path2)
        else:
            print("Метод compare_images не доступен в gee_client")
            return

        if 'error' in comparison:
            print(f"Ошибка: {comparison['error']}")
        else:
            print(f"\nРЕЗУЛЬТАТЫ СРАВНЕНИЯ:")
            print(f"   Измененные пиксели: {comparison.get('changed_pixels', 0):,}")
            print(f"   Всего пикселей: {comparison.get('total_pixels', 0):,}")
            print(f"   Процент изменений: {comparison.get('change_percentage', 0):.2f}%")
            print(f"   Уровень изменений: {comparison.get('change_level', 'N/A')}")

    def check_territory_changes(self):
        territories = self.db.get_all_territories()

        if not territories:
            print("\nНет территорий")
            return

        print("\nВыберите территорию:")
        for i, territory in enumerate(territories, 1):
            images = self.db.get_territory_images(territory['id'])
            print(f"{i}. {territory['name']} ({len(images)} изображений)")

        try:
            choice = int(input("\nНомер территории: "))
            if choice < 1 or choice > len(territories):
                print("Ошибка: Неверный выбор")
                return
        except ValueError:
            print("Ошибка: Введите число")
            return

        territory = territories[choice - 1]
        images = self.db.get_territory_images(territory['id'])
        print(f"\nПроверка изменений: {territory['name']}")
        print(f"   Найдено изображений: {len(images)}")

        if len(images) < 2:
            print(f"   Ошибка: Недостаточно изображений для сравнения")
            print(f"   Нужно минимум 2 изображения, сейчас {len(images)}")
            print(f"   Получите новое изображение через меню 'Получить спутниковое изображение'")
            return

        for i, img in enumerate(images[:2]):
            if not os.path.exists(img['image_path']):
                print(f"   Ошибка: Файл не найден: {img['image_path']}")
                print(f"   Возможно файл был удален или перемещен")
                return

        self.change_detector.detect_and_save_changes(territory['id'])

    def run_monitor_all(self):
        print("\n" + "=" * 60)
        print("ЗАПУСК МОНИТОРИНГА ВСЕХ ТЕРРИТОРИЙ")
        print("=" * 60)

        territories = self.db.get_all_territories()

        if not territories:
            print("\nНет активных территорий")
            return

        print(f"\nНайдено территорий: {len(territories)}")

        for territory in territories:
            print(f"\nТерритория: {territory['name']}")

            result = self.gee_client.get_satellite_image(
                territory['latitude'], territory['longitude']
            )

            if result and len(result) >= 3 and result[0]:
                success = result[0]
                path = result[1]
                date = result[2]
                message = result[3] if len(result) > 3 else ""

                if success:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = self.file_manager.get_safe_filename(territory['name']).replace('satellite_', '')
                    new_filename = f"monitor_{safe_name}"

                    # Получаем путь
                    original_folder = self.file_manager.folders['original']
                    new_path = os.path.join(original_folder, new_filename)

                    try:
                        shutil.move(path, new_path)
                        path = new_path
                        print(f"Изображение сохранено в: {new_path}")
                    except Exception as e:
                        print(f"Не удалось переместить файл: {e}")

                    print(f"   Получен снимок от {date}")

                    if hasattr(self.gee_client, 'analyze_image'):
                        analysis = self.gee_client.analyze_image(path)
                        if analysis and 'error' not in analysis:
                            cloud = analysis.get('cloud_cover', {}).get('percentage', 0)
                            print(f"   Облачность: {cloud:.1f}%")

                    file_size = os.path.getsize(path) if os.path.exists(path) else None
                    cloud_cover = analysis.get('cloud_cover', {}).get(
                        'percentage') if 'analysis' in locals() and analysis and 'error' not in analysis else None

                    self.db.add_image(
                        territory['id'], path, date,
                        cloud_cover, file_size
                    )

                    self.change_detector.detect_and_save_changes(territory['id'])
                else:
                    print(f"   Ошибка: {message}")
            else:
                print(f"   Ошибка при получении изображения")

        print(f"\nМониторинг завершен")

    def view_change_history(self):
        if hasattr(self.db, 'get_recent_changes'):
            changes = self.db.get_recent_changes(limit=20)
        else:
            print("Метод get_recent_changes не доступен")
            return

        if not changes:
            print("\nИзменений не обнаружено")
            return

        print(f"\nИСТОРИЯ ИЗМЕНЕНИЙ (последние {len(changes)}):")
        print("=" * 60)

        for change in changes:
            print(f"\nТерритория: {change.get('territory_name', 'N/A')}")
            print(f"Обнаружено: {change.get('detected_at', 'N/A')}")
            print(f"Изменения: {change.get('change_percentage', 0):.2f}%")
            print()

    def analyze_with_grid(self):
        print("\n" + "=" * 60)
        print("АНАЛИЗ С КООРДИНАТНОЙ СЕТКОЙ")
        print("=" * 60)

        territories = self.db.get_all_territories()
        if not territories:
            print("\nНет территорий для анализа")
            print("Сначала добавьте территории через меню 'Управление территориями'")
            return

        print("\nВыберите территорию:")
        for i, territory in enumerate(territories, 1):
            images = self.db.get_territory_images(territory['id'])
            print(f"{i}. {territory['name']} ({len(images)} изображений)")

        try:
            choice = int(input("\nНомер территории: "))
            if choice < 1 or choice > len(territories):
                print("Неверный выбор")
                return
        except ValueError:
            print("Введите число")
            return

        territory = territories[choice - 1]
        images = self.db.get_territory_images(territory['id'], limit=2)
        if len(images) < 2:
            print(f"\nНедостаточно изображений для анализа")
            print(f"Нужно минимум 2 изображения, сейчас {len(images)}")
            print(f"Получите новое изображение через меню 'Получить спутниковое изображение'")
            return

        new_image = images[0]
        old_image = images[1]

        if not os.path.exists(new_image['image_path']):
            print(f"Файл не найден: {new_image['image_path']}")
            return
        if not os.path.exists(old_image['image_path']):
            print(f"Файл не найден: {old_image['image_path']}")
            return

        print("\nВыберите размер ячейки сетки:")
        print("1. 16px - высокая детализация (мелкая сетка)")
        print("2. 32px - оптимально (средняя сетка)")
        print("3. 64px - обзорно (крупная сетка)")

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

        print(f"\nПАРАМЕТРЫ АНАЛИЗА:")
        print(f"   Территория: {territory['name']}")
        print(f"   Новый снимок: {new_image['capture_date']}")
        print(f"   Старый снимок: {old_image['capture_date']}")
        print(f"   Размер сетки: {grid_size} пикселей")

        print(f"\nЗапуск анализа с координатной сеткой...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        territory_slug = territory['name'].replace(' ', '_')

        results_filenames = {
            'visualization': f"grid_analysis_{territory_slug}_{timestamp}.jpg",
            'heatmap': f"heatmap_{territory_slug}_{timestamp}.jpg",
            'grid_image': f"grid_{territory_slug}_{timestamp}.jpg",
            'export': f"report_{territory_slug}_{timestamp}.json"
        }

        results = self.grid_analyzer.analyze_territory_with_grid(
            territory_info=territory,
            old_image_path=old_image['image_path'],
            new_image_path=new_image['image_path'],
            grid_size=grid_size
        )

        if results and results.get('success', False):
            print(f"\nАнализ завершен успешно!")

            moved_files = {}
            if results.get('visualization_path'):
                new_path = self.file_manager.get_path('analysis', results_filenames['visualization'])
                shutil.move(results['visualization_path'], new_path)
                results['visualization_path'] = new_path
                moved_files['visualization'] = new_path

            if results.get('heatmap_path'):
                new_path = self.file_manager.get_path('heatmaps', results_filenames['heatmap'])
                shutil.move(results['heatmap_path'], new_path)
                results['heatmap_path'] = new_path
                moved_files['heatmap'] = new_path

            if results.get('grid_image_path'):
                new_path = self.file_manager.get_path('grid', results_filenames['grid_image'])
                shutil.move(results['grid_image_path'], new_path)
                results['grid_image_path'] = new_path
                moved_files['grid'] = new_path

            if results.get('export_path'):
                new_path = self.file_manager.get_path('exports', results_filenames['export'])
                shutil.move(results['export_path'], new_path)
                results['export_path'] = new_path
                moved_files['export'] = new_path

            print("\nПоиск файлов сравнения с сеткой для уведомления...")

            comparison_grid_path = None
            grid_comparison_path = None

            # 1. Сначала ищем в папке comparison
            comparison_folder = self.file_manager.folders['comparison']
            territory_slug = territory['name'].replace(' ', '_')

            # Ищем файлы по разным шаблонам
            import glob

            # Все возможные паттерны для поиска
            patterns = [
                f"comparison_grid_{territory_slug}_*.jpg",
                f"grid_comparison_{territory_slug}_*.jpg",
                f"comparison_grid_*_{territory_slug}_*.jpg",
                f"grid_comparison_*_{territory_slug}_*.jpg",
                "comparison_grid_*.jpg",  # Все comparison_grid файлы
                "grid_comparison_*.jpg"  # Все grid_comparison файлы
            ]

            all_found_files = []
            for pattern in patterns:
                found = glob.glob(os.path.join(comparison_folder, pattern))
                all_found_files.extend(found)

            # Убираем дубликаты и проверяем существование
            all_found_files = list(set([f for f in all_found_files if os.path.exists(f)]))

            if all_found_files:
                # Сортируем по дате изменения (новые первые)
                all_found_files.sort(key=os.path.getmtime, reverse=True)

                print(f"  Найдено {len(all_found_files)} файлов сравнения:")
                for i, file_path in enumerate(all_found_files[:3], 1):
                    file_size = os.path.getsize(file_path) / 1024
                    print(f"    {i}. {os.path.basename(file_path)} ({file_size:.1f} KB)")

                # Берем первые 2 файла
                if len(all_found_files) >= 1:
                    comparison_grid_path = all_found_files[0]
                if len(all_found_files) >= 2:
                    grid_comparison_path = all_found_files[1]
            else:
                print("  Файлы сравнения не найдены. Создаем новый...")

                # 2. Создаем новый файл comparison_grid если не нашли
                try:
                    from grid_creator import GridCreator
                    creator = GridCreator(grid_size=32)

                    # ИСПРАВЛЕНО: old_image и new_image определены ранее в методе
                    grid_comparison_result = creator.create_comparison_grid(
                        before_path=old_image['image_path'],  # <- old_image определен выше
                        after_path=new_image['image_path'],   # <- new_image определен выше
                        territory_name=territory['name']
                    )

                    if grid_comparison_result and grid_comparison_result.get('success'):
                        temp_path = grid_comparison_result.get('comparison_path')
                        if temp_path and os.path.exists(temp_path):
                            # Перемещаем в папку comparison
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            new_filename = f"comparison_grid_{territory_slug}_{timestamp}.jpg"
                            new_path = os.path.join(comparison_folder, new_filename)
                            shutil.move(temp_path, new_path)
                            comparison_grid_path = new_path
                            print(f"  Создан новый файл сравнения: {os.path.basename(new_path)}")
                except Exception as e:
                    print(f"  Не удалось создать comparison_grid: {e}")

            # 3. ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ СО ВСЕМИ ФАЙЛАМИ
            print("\nПодготовка уведомления с результатами анализа...")

            # Рассчитываем процент изменений
            changed_cells = results.get('changed_cells', [])
            total_cells = results.get('total_cells', 0)
            change_percent = len(changed_cells) / total_cells * 100 if total_cells > 0 else 0

            # Создаем change_data для уведомления
            change_data = {
                'change_percentage': change_percent,
                'old_image_date': old_image['capture_date'],  # <- old_image определен выше
                'new_image_date': new_image['capture_date'],  # <- new_image определен выше
                'visualization_path': moved_files.get('visualization'),
                'grid_analysis_path': moved_files.get('export'),
                'changes_grid_path': moved_files.get('grid')
            }

            # Отправляем уведомление
            try:
                # Создаем менеджер уведомлений
                from notification import NotificationManager, EmailConfig

                email_config = EmailConfig()
                notification_manager = NotificationManager(email_config)

                success = notification_manager.send_change_notification(
                    territory_info=territory,
                    change_data=change_data,
                    latest_image_path=new_image['image_path'],
                    old_image_path=old_image['image_path'],
                    comparison_grid_path=comparison_grid_path,
                    grid_comparison_path=grid_comparison_path,
                    grid_image_path=moved_files.get('grid'),
                    heatmap_path=moved_files.get('heatmap'),
                    visualization_path=moved_files.get('visualization'),
                    changes_visualization_path=None
                )

                if success:
                    print("Уведомление успешно отправлено!")
                else:
                    print("Не удалось отправить уведомление")

            except Exception as e:
                print(f"Ошибка при отправке уведомления: {e}")
                import traceback
                traceback.print_exc()

            summary = results.get('analysis_summary', {})
            changed_cells = results.get('changed_cells', [])
            total_cells = results.get('total_cells', 0)

            print(f"\nРЕЗУЛЬТАТЫ АНАЛИЗА:")
            print(f"   Всего ячеек: {total_cells}")
            print(f"   Измененных ячеек: {len(changed_cells)}")
            print(f"   Процент изменений: {len(changed_cells) / total_cells * 100:.1f}%")
            print(f"   Среднее изменение: {summary.get('avg_pixel_change', 0):.1f}%")

            print(f"\nСОЗДАННЫЕ ФАЙЛЫ:")
            for file_type, file_path in moved_files.items():
                print(f"   {file_type}: {file_path}")

            detailed = input("\nПоказать детальный отчет? (y/n): ").lower()
            if detailed == 'y':
                self.grid_analyzer.print_detailed_report(results)

        else:
            error_msg = results.get('error', 'Неизвестная ошибка') if results else 'Нет результатов'
            print(f"\nОшибка анализа: {error_msg}")

    def create_grid_for_image(self):
        print("\n" + "=" * 60)
        print("СОЗДАНИЕ КООРДИНАТНОЙ СЕТКИ")
        print("=" * 60)

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

            images = self.db.get_territory_images(territory['id'], limit=1)
            if not images:
                print(f"Нет изображений для территории {territory['name']}")
                return

            image_path = images[0]['image_path']

            print(f"\nТерритория: {territory['name']}")
            print(f"   Координаты: {lat:.6f}°, {lon:.6f}°")
            print(f"   Изображение: {images[0]['capture_date']}")
            print(f"   Путь: {image_path}")

        elif source_choice == 2:
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

        print(f"\nСоздание сетки {grid_size}x{grid_size}...")

        result = self.grid_analyzer.create_grid_image(
            image_path=image_path,
            lat_center=lat,
            lon_center=lon,
            area_km=area_km,
            grid_size=grid_size
        )

        if result and result.get('success', False):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            location_name = f"grid_{lat:.4f}_{lon:.4f}"
            new_filename = f"{location_name}_{timestamp}.jpg"

            old_path = result.get('grid_image_path')
            new_path = self.file_manager.get_path('grid', new_filename)

            try:
                shutil.move(old_path, new_path)
                result['grid_image_path'] = new_path

                print(f"\nСетка создана успешно!")
                print(f"   Файл: {new_path}")

                open_img = input("\nОткрыть изображение с сеткой? (y/n): ").lower()
                if open_img == 'y':
                    try:
                        if sys.platform == "win32":
                            os.startfile(new_path)
                        elif sys.platform == "darwin":
                            import subprocess
                            subprocess.call(["open", new_path])
                        else:
                            import subprocess
                            subprocess.call(["xdg-open", new_path])
                        print("Изображение открыто")
                    except Exception as e:
                        print(f"Не удалось открыть файл: {e}")

            except Exception as e:
                print(f"Ошибка перемещения файла: {e}")
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Нет результатов'
            print(f"\nОшибка: {error_msg}")

    def compare_images_with_grid(self):
        print("\n" + "=" * 60)
        print("СРАВНЕНИЕ ИЗОБРАЖЕНИЙ С СЕТКОЙ")
        print("=" * 60)

        print("\nВведите пути к изображениям:")
        image1_path = input("Первое изображение (старое): ").strip()
        image2_path = input("Второе изображение (новое): ").strip()

        if not os.path.exists(image1_path):
            print(f"Файл не существует: {image1_path}")
            return
        if not os.path.exists(image2_path):
            print(f"Файл не существует: {image2_path}")
            return

        print("\nВведите координаты центра области:")
        try:
            lat = float(input("Широта: "))
            lon = float(input("Долгота: "))
        except ValueError:
            print("Неверный формат координат")
            return

        print("\nВыберите размер ячейки сетки:")
        print("1. 16px (детально)")
        print("2. 32px (оптимально)")
        print("3. 64px (быстро)")

        try:
            size_choice = int(input("Ваш выбор: "))
            grid_size = {1: 16, 2: 32, 3: 64}.get(size_choice, 32)
        except ValueError:
            grid_size = 32

        print(f"\nПАРАМЕТРЫ СРАВНЕНИЯ:")
        print(f"   Старое: {image1_path}")
        print(f"   Новое: {image2_path}")
        print(f"   Центр: {lat:.6f}°, {lon:.6f}°")
        print(f"   Сетка: {grid_size}px")

        print(f"\nСоздание сетки...")
        grid_result = self.grid_analyzer.create_grid_image(
            image_path=image2_path,
            lat_center=lat,
            lon_center=lon,
            area_km=2.0,
            grid_size=grid_size
        )

        if not grid_result or not grid_result.get('success', False):
            error_msg = grid_result.get('error', 'Неизвестно') if grid_result else 'Нет результатов'
            print(f"Ошибка создания сетки: {error_msg}")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        location_name = f"comparison_{lat:.4f}_{lon:.4f}"
        grid_filename = f"{location_name}_grid_{timestamp}.jpg"
        grid_new_path = self.file_manager.get_path('comparison', grid_filename)

        try:
            old_grid_path = grid_result.get('grid_image_path')
            shutil.move(old_grid_path, grid_new_path)
            grid_result['grid_image_path'] = grid_new_path
        except Exception as e:
            print(f"Не удалось переместить файл сетки: {e}")

        print(f"\nАнализ изменений...")
        analysis_result = self.grid_analyzer.analyze_changes_with_grid(
            image1_path=image1_path,
            image2_path=image2_path,
            grid_info=grid_result.get('grid_info', {})
        )

        if analysis_result and analysis_result.get('success', False):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filenames = {
                'visualization': f"comparison_vis_{location_name}_{timestamp}.jpg",
                'export': f"comparison_report_{location_name}_{timestamp}.json"
            }

            moved_files = {}

            if analysis_result.get('visualization_path'):
                new_path = self.file_manager.get_path('comparison', result_filenames['visualization'])
                try:
                    shutil.move(analysis_result['visualization_path'], new_path)
                    analysis_result['visualization_path'] = new_path
                    moved_files['visualization'] = new_path
                except Exception as e:
                    print(f"Не удалось переместить визуализацию: {e}")

            if analysis_result.get('export_path'):
                new_path = self.file_manager.get_path('exports', result_filenames['export'])
                try:
                    shutil.move(analysis_result['export_path'], new_path)
                    analysis_result['export_path'] = new_path
                    moved_files['export'] = new_path
                except Exception as e:
                    print(f"Не удалось переместить отчет: {e}")

            print(f"\nАнализ завершен!")

            summary = analysis_result.get('analysis_summary', {})
            changed = summary.get('changed_cells', 0)
            total = summary.get('total_cells', 1)

            print(f"\nКРАТКИЕ РЕЗУЛЬТАТЫ:")
            print(f"   Изменено ячеек: {changed}/{total} ({changed / total * 100:.1f}%)")
            print(f"   Среднее изменение: {summary.get('avg_pixel_change', 0):.1f}%")
            print(f"   Структурные изменения: {summary.get('structural_changes', 0)} ячеек")

            if moved_files:
                print(f"\nСОЗДАННЫЕ ФАЙЛЫ:")
                for file_type, file_path in moved_files.items():
                    print(f"   {file_type}: {file_path}")

            detailed = input("\nПоказать детальный отчет? (y/n): ").lower()
            if detailed == 'y':
                self.grid_analyzer.print_detailed_report(analysis_result)

            export = input("\nЭкспортировать результаты в JSON? (y/n): ").lower()
            if export == 'y':
                export_path = self.grid_analyzer.export_results_to_json(analysis_result)
                if export_path:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    export_filename = f"export_{location_name}_{timestamp}.json"
                    new_export_path = self.file_manager.get_path('exports', export_filename)
                    try:
                        shutil.move(export_path, new_export_path)
                        print(f"Результаты экспортированы в: {new_export_path}")
                    except Exception as e:
                        print(f"Результаты экспортированы в: {export_path}")
        else:
            error_msg = analysis_result.get('error', 'Неизвестно') if analysis_result else 'Нет результатов'
            print(f"\nОшибка анализа: {error_msg}")

    def show_grid_example(self):
        print("\n" + "=" * 60)
        print("ПРИМЕР РАБОТЫ С КООРДИНАТНОЙ СЕТКОЙ")
        print("=" * 60)

        print("\nКООРДИНАТНАЯ СЕТКА позволяет:")
        print("   • Точно определять координаты изменений")
        print("   • Анализировать изменения по ячейкам")
        print("   • Фильтровать изменения из-за освещения")
        print("   • Различать типы изменений (цвет, структура, освещение)")

        print("\nПРИНЦИП РАБОТЫ:")
        print("   1. Изображение делится на ячейки фиксированного размера")
        print("   2. Для каждой ячейки рассчитываются географические координаты")
        print("   3. Анализируются изменения внутри каждой ячейки")
        print("   4. Определяется тип изменений (освещение, цвет, структура)")

        print("\nЦВЕТОВАЯ СХЕМА В ВИЗУАЛИЗАЦИИ:")
        print("   Красный - структурные изменения (строительство, разрушение)")
        print("   Желтый - цветовые изменения (растительность, покраска)")
        print("   Синий - изменения освещения (тени, время суток)")
        print("   Зеленый - незначительные изменения")

        print("\nРАЗМЕРЫ СЕТКИ:")
        print("   • 16px - высокая детализация, много ячеек, медленно")
        print("   • 32px - оптимальный баланс детализации и скорости")
        print("   • 64px - обзорный анализ, быстро, меньше деталей")

        print("\nКООРДИНАТЫ:")
        print("   • Подписи показывают широту и долготу")
        print("   • Можно точно определить где произошли изменения")
        print("   • Координаты центра каждой ячейки сохраняются в отчете")

        input("\nНажмите Enter чтобы продолжить...")

    def organize_existing_files_option(self):
        print("\nОрганизация существующих файлов...")
        self.file_manager.organize_existing_files()

    def show_folder_structure(self):
        print("\n" + "=" * 60)
        print("СТРУКТУРА ПАПОК")
        print("=" * 60)

        def print_tree(directory, prefix=""):
            try:
                entries = sorted(os.listdir(directory))
                for i, entry in enumerate(entries):
                    path = os.path.join(directory, entry)
                    is_last = i == len(entries) - 1

                    if os.path.isdir(path):
                        print(f"{prefix}{'└── ' if is_last else '├── '} {entry}/")
                        extension = "    " if is_last else "│   "
                        print_tree(path, prefix + extension)
                    else:
                        size = os.path.getsize(path)
                        size_str = f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"
                        print(f"{prefix}{'└── ' if is_last else '├── '} {entry} ({size_str})")
            except Exception as e:
                print(f"{prefix}Ошибка доступа: {e}")

        base_path = self.file_manager.base_path
        if os.path.exists(base_path):
            print(f"\n{base_path}/")
            print_tree(base_path)
        else:
            print(f"\nПапка {base_path} не существует")

    def clean_temp_files(self):
        self.file_manager.clean_temp()

    def open_images_folder(self):
        folder_path = self.file_manager.base_path
        if os.path.exists(folder_path):
            try:
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.call(["open", folder_path])
                else:
                    import subprocess
                    subprocess.call(["xdg-open", folder_path])
                print(f"Папка открыта: {folder_path}")
            except Exception as e:
                print(f"Не удалось открыть папку: {e}")
        else:
            print(f"Папка не существует: {folder_path}")

    def system_info(self):
        print("\n" + "=" * 60)
        print("ИНФОРМАЦИЯ О СИСТЕМЕ")
        print("=" * 60)

        print(f"\nФАЙЛОВАЯ СИСТЕМА:")
        print(f"   Основная папка: {self.file_manager.base_path}")

        file_counts = {}
        total_size = 0

        for folder_name, folder_path in self.file_manager.folders.items():
            if os.path.exists(folder_path):
                files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                file_counts[folder_name] = len(files)

                folder_size = 0
                for file in files:
                    file_path = os.path.join(folder_path, file)
                    folder_size += os.path.getsize(file_path)
                total_size += folder_size

                size_str = f"{folder_size / 1024 / 1024:.1f}MB" if folder_size > 0 else "пусто"
                print(f"   {folder_name}: {len(files)} файлов ({size_str})")

        total_size_str = f"{total_size / 1024 / 1024:.1f}MB"
        print(f"   Всего файлов: {sum(file_counts.values())}")
        print(f"   Общий размер: {total_size_str}")

        try:
            if hasattr(self.db, 'get_statistics'):
                stats = self.db.get_statistics()
                print(f"\nСТАТИСТИКА БАЗЫ ДАННЫХ:")
                print(f"   Активных территорий: {stats.get('territories', 'N/A')}")
                print(f"   Всего изображений: {stats.get('images', 'N/A')}")
                print(f"   Обнаружено изменений: {stats.get('changes', 'N/A')}")
                print(f"   Последнее изображение: {stats.get('last_image_date', 'нет')}")
                print(f"   Последнее изменение: {stats.get('last_change_date', 'нет')}")
        except:
            print("\nСтатистика БД временно недоступна")

        print(f"\nКЭШ:")
        try:
            if hasattr(self.gee_client, 'get_cache_info'):
                cache_info = self.gee_client.get_cache_info()
                print(f"   Изображений в кэше: {cache_info.get('image_count', 0)}")
                print(f"   Размер кэша: {cache_info.get('total_size_mb', 0)} MB")
        except:
            print("   Информация о кэше временно недоступна")

        print(f"\nEMAIL УВЕДОМЛЕНИЯ:")
        if hasattr(self.change_detector, 'email_config') and self.change_detector.email_config:
            if self.change_detector.email_config.EMAIL_ENABLED:
                print(f"   Статус: Включены")
                print(f"   Отправитель: {self.change_detector.email_config.EMAIL_FROM}")
                print(f"   Получатель: {self.change_detector.email_config.EMAIL_TO}")
                print(f"   Порог: {self.change_detector.email_config.CHANGE_THRESHOLD}%")
            else:
                print(f"   Статус: Выключены")
        else:
            print(f"   Статус: Не настроены")

        territories = self.db.get_all_territories()
        if territories:
            print(f"\nАКТИВНЫЕ ТЕРРИТОРИИ:")
            for territory in territories[:3]:
                images = self.db.get_territory_images(territory['id'])
                print(f"   {territory['name']}: {len(images)} изображений")

            if len(territories) > 3:
                print(f"   ... и еще {len(territories) - 3} территорий")

        print(f"\nМОДУЛИ:")
        print(f"   Google Earth Engine: {'Да' if hasattr(self.gee_client, 'ee') else 'Нет'}")
        print(
            f"   OpenCV: {'Да' if hasattr(self.gee_client, 'cv2') and self.gee_client.cv2 is not None else 'Нет'}")
        print(f"   Pillow (PIL): Да")
        print(f"   Requests: Да")

    def setup_email_notifications(self):
        print("\n" + "=" * 60)
        print("НАСТРОЙКА EMAIL УВЕДОМЛЕНИЙ")
        print("=" * 60)

        try:
            from config_email import setup_email_notifications
            config = setup_email_notifications()
            self.change_detector = ChangeDetector(self.db, self.gee_client)

            if config.EMAIL_ENABLED:
                print("\nEmail уведомления активированы!")
                print(f"   Получатель: {config.EMAIL_TO}")
                print(f"   Порог изменений: {config.CHANGE_THRESHOLD}%")
                print(f"\nТеперь при значительных изменениях (> {config.CHANGE_THRESHOLD}%)")
                print(f"   уведомления будут приходить на: {config.EMAIL_TO}")
        except ImportError:
            print("Модуль config_email.py не найден")
            print("Создайте файл config_email.py с настройками email")
        except Exception as e:
            print(f"Ошибка настройки email: {e}")

    def clear_cache(self):
        print("\n" + "=" * 60)
        print("ОЧИСТКА КЭША")
        print("=" * 60)

        confirm = input("\nВНИМАНИЕ: Все изображения в кэше будут удалены. Продолжить? (y/n): ").lower()

        if confirm == 'y':
            if hasattr(self.gee_client, 'clear_cache'):
                result = self.gee_client.clear_cache()
                print(f"\n{result}")
            else:
                print("Метод clear_cache не доступен")
        else:
            print("\nОчистка отменена")

    def territories_menu(self):
        while True:
            print_territories_menu()
            choice = input("\nВыберите опцию: ").strip()

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
            elif choice == '6':
                self.manage_territory_images()
            else:
                print("Неверный выбор")

            input("\nНажмите Enter чтобы продолжить...")

    def analysis_menu(self):
        while True:
            print_analysis_menu()
            choice = input("\nВыберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.analyze_single_image()
            elif choice == '2':
                self.compare_images()
            else:
                print("Неверный выбор")

            input("\nНажмите Enter чтобы продолжить...")

    def grid_analysis_menu(self):
        while True:
            print_grid_menu()
            choice = input("\nВыберите опцию: ").strip()

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
                print("Неверный выбор")

            input("\nНажмите Enter чтобы продолжить...")

    def monitoring_menu(self):
        while True:
            print_monitoring_menu()
            choice = input("\nВыберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.check_territory_changes()
            elif choice == '2':
                self.run_monitor_all()
            elif choice == '3':
                self.view_change_history()
            else:
                print("Неверный выбор")

            input("\nНажмите Enter чтобы продолжить...")

    def settings_menu(self):
        while True:
            print_settings_menu()
            choice = input("\nВыберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.system_info()
            elif choice == '2':
                self.setup_email_notifications()
            elif choice == '3':
                self.clear_cache()
            else:
                print("Неверный выбор")

            input("\nНажмите Enter чтобы продолжить...")

    def files_menu(self):
        while True:
            print_files_menu()
            choice = input("\nВыберите опцию: ").strip()

            if choice == '0':
                break
            elif choice == '1':
                self.organize_existing_files_option()
            elif choice == '2':
                self.show_folder_structure()
            elif choice == '3':
                self.clean_temp_files()
            elif choice == '4':
                self.open_images_folder()
            elif choice == '5':
                self.find_and_delete_duplicates()
            else:
                print("Неверный выбор")

            input("\nНажмите Enter чтобы продолжить...")

    def run(self):
        print_header()

        while True:
            print_menu()

            try:
                choice = input("\nВыберите опцию (0-7): ").strip()

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
                elif choice == '7':
                    self.files_menu()
                else:
                    print("Неверный выбор. Попробуйте снова.")

            except KeyboardInterrupt:
                print("\nПрограмма прервана пользователем")
                break
            except Exception as e:
                print(f"\nНеожиданная ошибка: {e}")
                traceback.print_exc()
                input("\nНажмите Enter чтобы продолжить...")


def main():
    try:
        app = SatelliteMonitorApp()
        app.run()
    except KeyboardInterrupt:
        print("\nВыход")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()