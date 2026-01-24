"""
Детектор изменений на спутниковых снимках
"""

import os
from typing import Optional, Dict, Any
from database import Database
from ultimate_detector import detect_forest_changes
from gee_client import GEEClient
from improved_change_detector import detect_changes_improved
from grid_creator import GridCreator
import traceback


class ChangeDetector:
    def __init__(self, database: Database, gee_client: GEEClient):
        self.db = database
        self.gee = gee_client
        self.notifier = None
        self.email_config = None
        self.grid_creator = GridCreator(grid_size=32)  # Добавляем создатель сеток

        # Пробуем загрузить конфигурацию email
        self._load_email_config()

    def _load_email_config(self):
        """Загрузка конфигурации email из файла .env"""
        try:
            from config_email import EmailConfig
            self.email_config = EmailConfig()
            if self.email_config.EMAIL_ENABLED:
                from notification import NotificationManager
                self.notifier = NotificationManager(self.email_config)
                print("Email уведомления настроены")
        except Exception as e:
            print(f"Email уведомления недоступны: {e}")

    def detect_and_save_changes(self, territory_id: int, send_notification: bool = True) -> Optional[Dict[str, Any]]:
        """
        Обнаружение и сохранение изменений для территории

        Args:
            territory_id: ID территории
            send_notification: Отправлять ли уведомление по email

        Returns:
            Информация об изменениях или None
        """
        # Получаем последние два изображения территории
        images = self.db.get_territory_images(territory_id, limit=2)

        if len(images) < 2:
            print(f"Недостаточно изображений для сравнения (нужно минимум 2)")
            print(f"   Найдено: {len(images)} изображений")

            # Показываем какие изображения есть
            if images:
                print(f"   Доступные изображения:")
                for i, img in enumerate(images):
                    exists = "Да" if os.path.exists(img['image_path']) else "Нет"
                    print(f"     {i + 1}. {img['capture_date']} - {img['image_path']} (Файл существует: {exists})")

            return None

        new_image = images[0]  # самый новый
        old_image = images[1]  # предыдущий

        print(f"\nСравнение изображений:")
        print(f"   Новое: {new_image['capture_date']} (ID: {new_image['id']})")
        print(f"   Старое: {old_image['capture_date']} (ID: {old_image['id']})")

        # Проверяем существование файлов
        if not os.path.exists(new_image['image_path']):
            print(f"Ошибка: Файл не найден: {new_image['image_path']}")
            return None

        if not os.path.exists(old_image['image_path']):
            print(f"Ошибка: Файл не найден: {old_image['image_path']}")
            return None

        print(f"   Путь к новому: {new_image['image_path']}")
        print(f"   Путь к старому: {old_image['image_path']}")

        # Сравниваем изображения
        comparison = detect_changes_improved(
            old_image['image_path'],
            new_image['image_path']
        )

        if 'error' in comparison:
            print(f"Ошибка сравнения: {comparison['error']}")
            return None
        try:
            # 1. ПЕРВОЕ ДЕЛО: пытаемся выполнить сравнение
            comparison = detect_forest_changes(
                old_image['image_path'],
                new_image['image_path']
            )

            # 2. Если сравнение не удалось - запасной вариант
            if not comparison.get('success', False):
                print("Основной метод сравнения не удался, использую запасной...")
                comparison = self.gee.compare_images(
                    new_image['image_path'],
                    old_image['image_path']
                )

        except ImportError:
            # 3. Если модуль не найден (ImportError) - сразу используем стандартный метод
            print("Модуль сравнения не найден, использую стандартный метод...")
            comparison = self.gee.compare_images(
                new_image['image_path'],
                old_image['image_path']
            )
        except Exception as e:
            # 4. Другие возможные ошибки
            print(f"Ошибка при сравнении изображений: {e}")
            comparison = {
                'success': False,
                'error': str(e)
            }

        # 5. ТОЛЬКО ПОСЛЕ ВСЕХ ПОПЫТОК проверяем на ошибки
        if 'error' in comparison or not comparison.get('success', False):
            print(f"Ошибка сравнения: {comparison.get('error', 'Неизвестная ошибка')}")
            return None

        # 6. Если всё успешно - продолжаем работу
        print("Сравнение выполнено успешно!")

        change_percentage = comparison.get('change_percentage', 0)

        print(f"\nРезультат: {change_percentage:.2f}% изменений")
        print(f"Уровень: {comparison.get('change_level', 'неизвестно')}")
        print(f"Значимость: {comparison.get('significance', 'неизвестно')}")

        # Определяем уровень изменений если его нет
        if 'change_level' not in comparison:
            if change_percentage > 50:
                comparison['change_level'] = 'критические'
            elif change_percentage > 20:
                comparison['change_level'] = 'высокие'
            elif change_percentage > 10:
                comparison['change_level'] = 'средние'
            elif change_percentage > 5:
                comparison['change_level'] = 'низкие'
            else:
                comparison['change_level'] = 'минимальные'

            if 'significance' not in comparison:
                comparison['significance'] = comparison['change_level']

        # Сохраняем в базу данных
        change_id = self.db.add_change(
            territory_id,
            old_image['id'],
            new_image['id'],
            change_percentage
        )

        print(f"Изменения сохранены в БД с ID: {change_id}")

        # Отправляем уведомление если нужно
        if send_notification and self._should_send_notification(change_percentage):
            self._send_notification(territory_id, change_id, comparison, new_image, old_image)

        # Проверяем на значительные изменения
        if change_percentage > 10:
            print(f"ВНИМАНИЕ: Значительные изменения обнаружены!")
        elif change_percentage > 5:
            print(f"Заметные изменения обнаружены")
        else:
            print(f"Изменения незначительны")

        return {
            'change_id': change_id,
            'change_percentage': change_percentage,
            'new_image_date': new_image['capture_date'],
            'old_image_date': old_image['capture_date'],
            'change_level': comparison['change_level'],
            'significance': comparison['significance']
        }

    def _should_send_notification(self, change_percentage: float) -> bool:
        """Проверяет, нужно ли отправлять уведомление"""
        if not self.email_config or not hasattr(self.email_config, 'CHANGE_THRESHOLD'):
            return change_percentage > 5.0  # По умолчанию 5%

        if not self.email_config.EMAIL_ENABLED:
            return False

        return change_percentage > self.email_config.CHANGE_THRESHOLD

    def _create_grid_visualizations(self, territory, new_image_path, old_image_path, comparison):
        """Создает все сеточные визуализации"""
        print("\n📐 СОЗДАНИЕ СЕТОЧНЫХ ВИЗУАЛИЗАЦИЙ...")
        grid_files = {}

        try:
            # 1. Основная сетка нового изображения
            print("   Создание основной сетки...")
            grid_result = self.grid_creator.create_grid_for_email(
                image_path=new_image_path,
                lat=territory.get('latitude', 0),
                lon=territory.get('longitude', 0),
                territory_name=territory.get('name', 'Территория')
            )
            if grid_result.get('success'):
                grid_files['grid_image'] = grid_result['grid_path']
                print(f"     ✅ Основная сетка: {os.path.basename(grid_result['grid_path'])}")

            # 2. Сравнительная сетка
            print("   Создание сравнительной сетки...")
            comparison_result = self.grid_creator.create_comparison_grid(
                before_path=old_image_path,
                after_path=new_image_path,
                territory_name=territory.get('name', 'Территория')
            )
            if comparison_result.get('success'):
                grid_files['comparison_grid'] = comparison_result['comparison_path']
                print(f"     ✅ Сравнительная сетка: {os.path.basename(comparison_result['comparison_path'])}")

            # 3. Сетка с изменениями (если есть маска)
            if 'mask_path' in comparison and os.path.exists(comparison.get('mask_path', '')):
                print("   Создание сетки с изменениями...")
                changes_result = self.grid_creator.create_grid_with_changes(
                    image_path=new_image_path,
                    changes_mask_path=comparison['mask_path'],
                    territory_name=territory.get('name', 'Территория')
                )
                if changes_result.get('success'):
                    grid_files['changes_grid'] = changes_result['changes_grid_path']
                    print(f"     ✅ Сетка с изменениями: {os.path.basename(changes_result['changes_grid_path'])}")

            # 4. Сеточный анализ (если есть визуализация сетки)
            if 'grid_visualization_path' in comparison and os.path.exists(
                    comparison.get('grid_visualization_path', '')):
                grid_files['grid_analysis'] = comparison['grid_visualization_path']
                print(f"     ✅ Сеточный анализ: {os.path.basename(comparison['grid_visualization_path'])}")

            # 5. Тепловая карта (если есть)
            if 'heatmap_path' in comparison and os.path.exists(comparison.get('heatmap_path', '')):
                grid_files['heatmap'] = comparison['heatmap_path']
                print(f"     ✅ Тепловая карта: {os.path.basename(comparison['heatmap_path'])}")

            return grid_files

        except Exception as e:
            print(f"     ❌ Ошибка создания сеток: {e}")
            traceback.print_exc()
            return None

    def _send_notification(self, territory_id: int, change_id: int,
                           comparison: Dict[str, Any], new_image: Dict[str, Any],
                           old_image: Dict[str, Any]):
        """Отправка уведомления по email С СЕТОЧНЫМИ ВИЗУАЛИЗАЦИЯМИ"""
        try:
            print(f"\n{'=' * 60}")
            print("📧 НАЧАЛО ОТПРАВКИ УВЕДОМЛЕНИЯ СО СЕТКАМИ")
            print(f"{'=' * 60}")

            if not self.notifier or not self.email_config:
                print("Уведомления отключены или не настроены")
                return

            # Получаем информацию о территории
            territory = self.db.get_territory(territory_id)
            if not territory:
                print("Ошибка: Не удалось получить информацию о территории")
                return

            print(f"📍 Территория: {territory.get('name', 'Неизвестно')}")
            print(f"📍 Координаты: {territory.get('latitude', 0):.6f}, {territory.get('longitude', 0):.6f}")

            # Создаем данные об изменениях
            change_percentage = comparison.get('change_percentage', 0)
            change_level = comparison.get('change_level', 'неизвестно')

            change_data = {
                'change_percentage': change_percentage,
                'change_level': change_level,
                'new_image_date': new_image['capture_date'],
                'old_image_date': old_image['capture_date'],
                'confidence': 0.85,
                'change_type': change_level,
                'significance': comparison.get('significance', 'Неизвестно'),
                'has_visualization': False,
                'has_grid_visualization': False
            }

            # Добавляем информацию о сезонности
            if 'is_seasonal_change' in comparison:
                change_data['is_seasonal'] = comparison['is_seasonal_change']
                change_data['seasonal_reason'] = comparison.get('seasonal_reason', '')
                change_data['brightness_ratio'] = comparison.get('brightness_ratio', 1.0)
                change_data['green_ratio'] = comparison.get('green_ratio', 1.0)

            # Получаем пути к изображениям
            new_image_path = new_image['image_path']
            old_image_path = old_image['image_path']

            print(f"\n📁 ФАЙЛЫ:")
            print(
                f"   Новый снимок: {os.path.basename(new_image_path)} ({'существует' if os.path.exists(new_image_path) else 'НЕ СУЩЕСТВУЕТ'})")
            print(
                f"   Старый снимок: {os.path.basename(old_image_path)} ({'существует' if os.path.exists(old_image_path) else 'НЕ СУЩЕСТВУЕТ'})")

            # ========== ШАГ 1: СОЗДАЕМ СЕТОЧНЫЕ ВИЗУАЛИЗАЦИИ ==========
            print(f"\n{'─' * 60}")
            print("📐 СОЗДАНИЕ СЕТОЧНЫХ ВИЗУАЛИЗАЦИЙ")
            print(f"{'─' * 60}")

            grid_files = {}

            try:
                # Проверяем доступность GridCreator
                if not hasattr(self, 'grid_creator') or self.grid_creator is None:
                    print("❌ GridCreator не инициализирован!")
                    self.grid_creator = GridCreator(grid_size=32)
                    print("✅ GridCreator создан заново")

                print(f"   GridCreator: {self.grid_creator}")
                print(f"   Размер сетки: {self.grid_creator.grid_size}px")

                territory_name = territory.get('name', 'Территория')

                # 1. Основная сетка нового изображения
                print(f"\n   1. СОЗДАНИЕ ОСНОВНОЙ СЕТКИ...")
                try:
                    grid_result = self.grid_creator.create_grid_for_email(
                        image_path=new_image_path,
                        lat=territory.get('latitude', 0),
                        lon=territory.get('longitude', 0),
                        territory_name=territory_name
                    )

                    if grid_result.get('success') and os.path.exists(grid_result.get('grid_path', '')):
                        grid_files['grid_image'] = grid_result['grid_path']
                        print(f"      ✅ Создана: {os.path.basename(grid_result['grid_path'])}")
                        size = os.path.getsize(grid_result['grid_path']) / 1024
                        print(f"      📏 Размер: {size:.1f} KB")
                    else:
                        print(f"      ❌ Ошибка: {grid_result.get('error', 'Неизвестная ошибка')}")
                except Exception as e:
                    print(f"      ❌ Исключение: {e}")

                # 2. Сравнительная сетка
                print(f"\n   2. СОЗДАНИЕ СРАВНИТЕЛЬНОЙ СЕТКИ...")
                try:
                    comparison_result = self.grid_creator.create_comparison_grid(
                        before_path=old_image_path,
                        after_path=new_image_path,
                        territory_name=territory_name
                    )

                    if comparison_result.get('success') and os.path.exists(
                            comparison_result.get('comparison_path', '')):
                        grid_files['comparison_grid'] = comparison_result['comparison_path']
                        print(f"      ✅ Создана: {os.path.basename(comparison_result['comparison_path'])}")
                        size = os.path.getsize(comparison_result['comparison_path']) / 1024
                        print(f"      📏 Размер: {size:.1f} KB")
                    else:
                        print(f"      ❌ Ошибка: {comparison_result.get('error', 'Неизвестная ошибка')}")
                except Exception as e:
                    print(f"      ❌ Исключение: {e}")

                # 3. Сетка с изменениями
                print(f"\n   3. СОЗДАНИЕ СЕТКИ С ИЗМЕНЕНИЯМИ...")
                try:
                    mask_path = comparison.get('mask_path', '')
                    if mask_path and os.path.exists(mask_path):
                        print(f"      Найдена маска: {os.path.basename(mask_path)}")
                        changes_result = self.grid_creator.create_grid_with_changes(
                            image_path=new_image_path,
                            changes_mask_path=mask_path,
                            territory_name=territory_name
                        )

                        if changes_result.get('success') and os.path.exists(
                                changes_result.get('changes_grid_path', '')):
                            grid_files['changes_grid'] = changes_result['changes_grid_path']
                            print(f"      ✅ Создана: {os.path.basename(changes_result['changes_grid_path'])}")
                            size = os.path.getsize(changes_result['changes_grid_path']) / 1024
                            print(f"      📏 Размер: {size:.1f} KB")
                        else:
                            print(f"      ❌ Ошибка: {changes_result.get('error', 'Неизвестная ошибка')}")
                    else:
                        print(f"      ⚠️ Маска не найдена, пропускаем")
                except Exception as e:
                    print(f"      ❌ Исключение: {e}")

                # 4. Проверяем, есть ли файлы визуализации из comparison
                print(f"\n   4. ПРОВЕРКА ДОПОЛНИТЕЛЬНЫХ ФАЙЛОВ...")
                for key in ['visualization_path', 'grid_visualization_path', 'heatmap_path']:
                    if key in comparison:
                        path = comparison[key]
                        if path and os.path.exists(path):
                            if key == 'visualization_path':
                                grid_files['visualization'] = path
                                print(f"      ✅ Визуализация: {os.path.basename(path)}")
                            elif key == 'grid_visualization_path':
                                grid_files['grid_analysis'] = path
                                print(f"      ✅ Сеточный анализ: {os.path.basename(path)}")
                            elif key == 'heatmap_path':
                                grid_files['heatmap'] = path
                                print(f"      ✅ Тепловая карта: {os.path.basename(path)}")

                            size = os.path.getsize(path) / 1024
                            print(f"      📏 Размер: {size:.1f} KB")

                print(f"\n📊 ИТОГО СОЗДАНО СЕТОК: {len(grid_files)}")
                for file_type, file_path in grid_files.items():
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path) / 1024
                        print(f"   • {file_type}: {os.path.basename(file_path)} ({size:.1f} KB)")
                    else:
                        print(f"   ⚠️ {file_type}: файл не существует")

            except Exception as e:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при создании сеток: {e}")
                import traceback
                traceback.print_exc()
                grid_files = {}

            # ========== ШАГ 2: ПОДГОТОВКА К ОТПРАВКЕ ==========
            print(f"\n{'─' * 60}")
            print("📤 ПОДГОТОВКА К ОТПРАВКЕ EMAIL")
            print(f"{'─' * 60}")

            # Собираем ВСЕ файлы для отправки
            all_files = {}

            # Обязательные файлы
            if new_image_path and os.path.exists(new_image_path):
                all_files['latest_image'] = new_image_path
            if old_image_path and os.path.exists(old_image_path):
                all_files['old_image'] = old_image_path

            # Добавляем все сеточные файлы
            for file_type, file_path in grid_files.items():
                if file_path and os.path.exists(file_path):
                    all_files[file_type] = file_path

            # Добавляем визуализацию из сравнения если есть
            if 'visualization_path' in comparison:
                viz_path = comparison['visualization_path']
                if viz_path and os.path.exists(viz_path):
                    all_files['comparison_visualization'] = viz_path

            print(f"   Всего файлов для отправки: {len(all_files)}")

            if len(all_files) == 0:
                print("❌ Нет файлов для отправки!")
                return

            # Выводим список файлов
            for file_type, file_path in all_files.items():
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path) / 1024
                    print(f"   ✓ {file_type}: {os.path.basename(file_path)} ({size:.1f} KB)")
                else:
                    print(f"   ⚠️ {file_type}: файл не существует!")

            # ========== ШАГ 3: ОТПРАВКА EMAIL ==========
            print(f"\n{'─' * 60}")
            print("🚀 ОТПРАВКА EMAIL СО СЕТКАМИ")
            print(f"{'─' * 60}")

            try:
                # Создаем заголовок для сеточного анализа
                grid_count = sum(1 for key in all_files if 'grid' in key.lower())
                subject = f"📐 СЕТОЧНЫЙ АНАЛИЗ ({grid_count} файлов): {territory.get('name', '')} - {change_percentage:.1f}%"

                print(f"   Тема письма: {subject}")
                print(f"   Получатель: {self.email_config.EMAIL_TO}")
                print(f"   Всего вложений: {len(all_files)}")

                # Пробуем отправить с помощью существующего метода
                # Сначала проверяем, какие параметры принимает метод
                import inspect

                try:
                    sig = inspect.signature(self.notifier.send_change_notification)
                    params = list(sig.parameters.keys())

                    print(f"\n   📋 Параметры метода send_change_notification:")
                    for param in params:
                        print(f"      • {param}")

                    # Создаем словарь аргументов
                    kwargs = {
                        'territory_info': territory,
                        'change_data': change_data
                    }

                    # Добавляем ВСЕ возможные файлы как параметры
                    if 'latest_image_path' in params and 'latest_image' in all_files:
                        kwargs['latest_image_path'] = all_files['latest_image']

                    if 'old_image_path' in params and 'old_image' in all_files:
                        kwargs['old_image_path'] = all_files['old_image']

                    if 'visualization_path' in params and 'visualization' in all_files:
                        kwargs['visualization_path'] = all_files['visualization']

                    if 'grid_image_path' in params and 'grid_image' in all_files:
                        kwargs['grid_image_path'] = all_files['grid_image']

                    if 'comparison_grid_path' in params and 'comparison_grid' in all_files:
                        kwargs['comparison_grid_path'] = all_files['comparison_grid']

                    if 'changes_grid_path' in params and 'changes_grid' in all_files:
                        kwargs['changes_grid_path'] = all_files['changes_grid']

                    if 'grid_analysis_path' in params and 'grid_analysis' in all_files:
                        kwargs['grid_analysis_path'] = all_files['grid_analysis']

                    if 'heatmap_path' in params and 'heatmap' in all_files:
                        kwargs['heatmap_path'] = all_files['heatmap']

                    if 'comparison_visualization_path' in params and 'comparison_visualization' in all_files:
                        kwargs['comparison_visualization_path'] = all_files['comparison_visualization']

                    print(f"\n   🚀 Отправка с {len(kwargs)} параметрами...")

                    # Отправляем email!
                    success = self.notifier.send_change_notification(**kwargs)

                    if success:
                        print(f"\n✅ УСПЕХ! Email с сетками отправлен!")
                        print(f"   📬 Получатель: {self.email_config.EMAIL_TO}")
                        print(f"   📁 Вложений: {len(all_files)} файлов")
                        print(f"   📈 Изменения: {change_percentage:.1f}%")
                        print(f"   🏷️ Тема: {subject}")
                    else:
                        print(f"\n❌ ОШИБКА отправки email")

                except Exception as sig_error:
                    print(f"❌ Ошибка определения параметров: {sig_error}")

                    # Пробуем базовый вариант
                    print("🔄 Пробую базовый метод отправки...")
                    success = self.notifier.send_change_notification(
                        territory_info=territory,
                        change_data=change_data
                    )

                    if success:
                        print(f"✅ Базовый email отправлен (без сеток)")
                    else:
                        print(f"❌ Базовый email не отправлен")

            except Exception as email_error:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ОТПРАВКЕ EMAIL: {email_error}")
                import traceback
                traceback.print_exc()

            # ========== ШАГ 4: ОЧИСТКА ==========
            print(f"\n{'─' * 60}")
            print("🧹 ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ")
            print(f"{'─' * 60}")

            # Очищаем только те файлы, которые были созданы GridCreator
            temp_files_to_clean = []
            for file_type in ['grid_image', 'comparison_grid', 'changes_grid']:
                if file_type in grid_files and grid_files[file_type] and os.path.exists(grid_files[file_type]):
                    temp_files_to_clean.append(grid_files[file_type])

            for file_path in temp_files_to_clean:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"   🗑️ Удален: {os.path.basename(file_path)}")
                except Exception as clean_error:
                    print(f"   ⚠️ Не удалось удалить {file_path}: {clean_error}")

            print(f"\n{'=' * 60}")
            print("🎉 ОТПРАВКА УВЕДОМЛЕНИЯ ЗАВЕРШЕНА")
            print(f"{'=' * 60}")

        except Exception as e:
            print(f"\n{'=' * 60}")
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА В _send_notification: {e}")
            print(f"{'=' * 60}")
            import traceback
            traceback.print_exc()