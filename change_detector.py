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
        self.grid_creator = GridCreator(grid_size=32)

        self._load_email_config()

    def _load_email_config(self):
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
        images = self.db.get_territory_images(territory_id, limit=2)

        if len(images) < 2:
            print(f"Недостаточно изображений для сравнения (нужно минимум 2)")
            print(f"   Найдено: {len(images)} изображений")

            if images:
                print(f"   Доступные изображения:")
                for i, img in enumerate(images):
                    exists = "Да" if os.path.exists(img['image_path']) else "Нет"
                    print(f"     {i + 1}. {img['capture_date']} - {img['image_path']} (Файл существует: {exists})")

            return None

        new_image = images[0]
        old_image = images[1]

        print(f"\nСравнение изображений:")
        print(f"   Новое: {new_image['capture_date']} (ID: {new_image['id']})")
        print(f"   Старое: {old_image['capture_date']} (ID: {old_image['id']})")
        print(f"   Путь к новому: {new_image['image_path']}")
        print(f"   Путь к старому: {old_image['image_path']}")

        comparison = detect_changes_improved(
            old_image['image_path'],
            new_image['image_path']
        )

        if 'error' in comparison:
            print(f"Ошибка в улучшенном детекторе: {comparison['error']}")

            try:
                comparison = detect_forest_changes(
                    old_image['image_path'],
                    new_image['image_path']
                )

                if not comparison.get('success', False):
                    print("Основной метод сравнения не удался, использую запасной...")
                    comparison = self.gee.compare_images(
                        new_image['image_path'],
                        old_image['image_path']
                    )

            except ImportError:
                print("Модуль сравнения не найден, использую стандартный метод...")
                comparison = self.gee.compare_images(
                    new_image['image_path'],
                    old_image['image_path']
                )
            except Exception as e:
                print(f"Ошибка при сравнении изображений: {e}")
                comparison = {
                    'success': False,
                    'error': str(e)
                }

        # === Обработка результатов ===
        if 'error' in comparison or not comparison.get('success', False):
            print(f"Ошибка сравнения: {comparison.get('error', 'Неизвестная ошибка')}")
            return None

        print("Сравнение выполнено успешно!")

        # процент изменений из результатов
        if 'real_change_percentage' in comparison:
            change_percentage = comparison['real_change_percentage']
        else:
            change_percentage = comparison.get('change_percentage', 0)

        print(f"\nРЕЗУЛЬТАТЫ: {change_percentage:.2f}% изменений")


        if 'change_type' in comparison:
            change_level = comparison.get('change_type', 'неизвестно')
            significance = comparison.get('significance', 'неизвестно')
            is_seasonal = comparison.get('is_seasonal', False)
            change_details = comparison.get('details', {})

            print(f"Тип изменений: {change_level}")
            print(f"Значимость: {significance}")
            print(f"Сезонные: {'Да' if is_seasonal else 'Нет'}")

            if change_details:
                print(f"Детали:")
                for key, value in change_details.items():
                    print(f"  {key}: {value}")
        else:
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

        comparison['new_image_date'] = new_image['capture_date']
        comparison['old_image_date'] = old_image['capture_date']
        comparison['new_image_id'] = new_image['id']
        comparison['old_image_id'] = old_image['id']

        # Сохраняем изменение в БД
        change_id = self.db.add_change(
            territory_id,
            old_image['id'],
            new_image['id'],
            change_percentage
        )

        print(f"Изменения сохранены в БД с ID: {change_id}")

        # === Передаем все данные в уведомление ===
        if send_notification and self._should_send_notification(change_percentage):
            print(f"\nОтправка уведомления с полными результатами...")
            self._send_notification(territory_id, change_id, comparison, new_image, old_image)

        # Вывод предупреждений
        if change_percentage > 10:
            print(f"ВНИМАНИЕ: Значительные изменения обнаружены!")
        elif change_percentage > 5:
            print(f"Заметные изменения обнаружены")
        else:
            print(f"Изменения незначительны")

        # Возвращаем полные результаты
        return {
            'change_id': change_id,
            'change_percentage': change_percentage,
            'new_image_date': new_image['capture_date'],
            'old_image_date': old_image['capture_date'],
            'change_level': comparison.get('change_level', 'неизвестно'),
            'significance': comparison.get('significance', 'неизвестно'),
            'change_type': comparison.get('change_type', 'неизвестно'),
            'is_seasonal': comparison.get('is_seasonal', False),
            'details': comparison.get('details', {}),
            'visualization_path': comparison.get('visualization_path'),
            'mask_path': comparison.get('mask_path'),
            'heatmap_path': comparison.get('heatmap_path'),
            'grid_visualization_path': comparison.get('grid_visualization_path')
        }

    def _should_send_notification(self, change_percentage: float) -> bool:
        if not self.email_config or not hasattr(self.email_config, 'CHANGE_THRESHOLD'):
            return change_percentage > 5.0

        if not self.email_config.EMAIL_ENABLED:
            return False

        return change_percentage > self.email_config.CHANGE_THRESHOLD

    def _create_grid_visualizations(self, territory, new_image_path, old_image_path, comparison):
        print("\nСОЗДАНИЕ СЕТОЧНЫХ ВИЗУАЛИЗАЦИЙ...")
        grid_files = {}

        try:
            grid_result = self.grid_creator.create_grid_for_email(
                image_path=new_image_path,
                lat=territory.get('latitude', 0),
                lon=territory.get('longitude', 0),
                territory_name=territory.get('name', 'Территория')
            )
            if grid_result.get('success'):
                grid_files['grid_image'] = grid_result['grid_path']

            comparison_result = self.grid_creator.create_comparison_grid(
                before_path=old_image_path,
                after_path=new_image_path,
                territory_name=territory.get('name', 'Территория')
            )
            if comparison_result.get('success'):
                grid_files['comparison_grid'] = comparison_result['comparison_path']

            if 'mask_path' in comparison and os.path.exists(comparison.get('mask_path', '')):
                changes_result = self.grid_creator.create_grid_with_changes(
                    image_path=new_image_path,
                    changes_mask_path=comparison['mask_path'],
                    territory_name=territory.get('name', 'Территория')
                )
                if changes_result.get('success'):
                    grid_files['changes_grid'] = changes_result['changes_grid_path']

            if 'grid_visualization_path' in comparison and os.path.exists(
                    comparison.get('grid_visualization_path', '')):
                grid_files['grid_analysis'] = comparison['grid_visualization_path']

            if 'heatmap_path' in comparison and os.path.exists(comparison.get('heatmap_path', '')):
                grid_files['heatmap'] = comparison['heatmap_path']

            return grid_files

        except Exception as e:
            print(f"Ошибка создания сеток: {e}")
            traceback.print_exc()
            return None

    def _send_notification(self, territory_id: int, change_id: int,
                           comparison: Dict[str, Any], new_image: Dict[str, Any],
                           old_image: Dict[str, Any]):
        try:
            print(f"\n{'=' * 60}")
            print("НАЧАЛО ОТПРАВКИ УВЕДОМЛЕНИЯ С ПОЛНЫМИ РЕЗУЛЬТАТАМИ")
            print(f"{'=' * 60}")

            if not self.notifier or not self.email_config:
                print("Уведомления отключены или не настроены")
                return

            territory = self.db.get_territory(territory_id)
            if not territory:
                print("Ошибка: Не удалось получить информацию о территории")
                return

            print(f"Территория: {territory.get('name', 'Неизвестно')}")
            print(f"Координаты: {territory.get('latitude', 0):.6f}, {territory.get('longitude', 0):.6f}")

            change_percentage = comparison.get('real_change_percentage', comparison.get('change_percentage', 0))
            change_level = comparison.get('change_type', comparison.get('change_level', 'неизвестно'))
            significance = comparison.get('significance', 'неизвестно')
            is_seasonal = comparison.get('is_seasonal', False)

            # === Создаем расширенные данные для уведомления ===
            change_data = {
                'change_percentage': change_percentage,
                'change_level': change_level,
                'new_image_date': new_image['capture_date'],
                'old_image_date': old_image['capture_date'],
                'confidence': 0.85,
                'change_type': change_level,
                'significance': significance,
                'is_seasonal': is_seasonal,
                'has_visualization': False,
                'has_grid_visualization': False,
                # Добавляем подробные данные из improved детектора
                'real_change_percentage': comparison.get('real_change_percentage', change_percentage),
                'base_percentage': comparison.get('base_percentage', change_percentage),
                'changed_pixels': comparison.get('changed_pixels', 0),
                'total_pixels': comparison.get('total_pixels', 0),
                'change_type_detailed': comparison.get('change_type', 'неизвестно'),
                'details': comparison.get('details', {})
            }

            # Добавляем сезонные данные, если есть
            if 'is_seasonal_change' in comparison:
                change_data['is_seasonal'] = comparison['is_seasonal_change']
                change_data['seasonal_reason'] = comparison.get('seasonal_reason', '')
                change_data['brightness_ratio'] = comparison.get('brightness_ratio', 1.0)
                change_data['green_ratio'] = comparison.get('green_ratio', 1.0)


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

            if 'is_seasonal_change' in comparison:
                change_data['is_seasonal'] = comparison['is_seasonal_change']
                change_data['seasonal_reason'] = comparison.get('seasonal_reason', '')
                change_data['brightness_ratio'] = comparison.get('brightness_ratio', 1.0)
                change_data['green_ratio'] = comparison.get('green_ratio', 1.0)

            new_image_path = new_image['image_path']
            old_image_path = old_image['image_path']

            print(f"\nФАЙЛЫ:")
            print(
                f"   Новый снимок: {os.path.basename(new_image_path)} ({'существует' if os.path.exists(new_image_path) else 'НЕ СУЩЕСТВУЕТ'})")
            print(
                f"   Старый снимок: {os.path.basename(old_image_path)} ({'существует' if os.path.exists(old_image_path) else 'НЕ СУЩЕСТВУЕТ'})")

            print(f"\n{'─' * 60}")
            print("СОЗДАНИЕ СЕТОЧНЫХ ВИЗУАЛИЗАЦИЙ")
            print(f"{'─' * 60}")

            grid_files = {}

            try:
                if not hasattr(self, 'grid_creator') or self.grid_creator is None:
                    self.grid_creator = GridCreator(grid_size=32)

                territory_name = territory.get('name', 'Территория')

                grid_result = self.grid_creator.create_grid_for_email(
                    image_path=new_image_path,
                    lat=territory.get('latitude', 0),
                    lon=territory.get('longitude', 0),
                    territory_name=territory_name
                )

                if grid_result.get('success') and os.path.exists(grid_result.get('grid_path', '')):
                    grid_files['grid_image'] = grid_result['grid_path']

                comparison_result = self.grid_creator.create_comparison_grid(
                    before_path=old_image_path,
                    after_path=new_image_path,
                    territory_name=territory_name
                )

                if comparison_result.get('success') and os.path.exists(
                        comparison_result.get('comparison_path', '')):
                    grid_files['comparison_grid'] = comparison_result['comparison_path']

                mask_path = comparison.get('mask_path', '')
                if mask_path and os.path.exists(mask_path):
                    changes_result = self.grid_creator.create_grid_with_changes(
                        image_path=new_image_path,
                        changes_mask_path=mask_path,
                        territory_name=territory_name
                    )

                    if changes_result.get('success') and os.path.exists(
                            changes_result.get('changes_grid_path', '')):
                        grid_files['changes_grid'] = changes_result['changes_grid_path']

                for key in ['visualization_path', 'grid_visualization_path', 'heatmap_path']:
                    if key in comparison:
                        path = comparison[key]
                        if path and os.path.exists(path):
                            if key == 'visualization_path':
                                grid_files['visualization'] = path
                            elif key == 'grid_visualization_path':
                                grid_files['grid_analysis'] = path
                            elif key == 'heatmap_path':
                                grid_files['heatmap'] = path

            except Exception as e:
                print(f"КРИТИЧЕСКАЯ ОШИБКА при создании сеток: {e}")
                import traceback
                traceback.print_exc()
                grid_files = {}

            print(f"\n{'─' * 60}")
            print("ПОДГОТОВКА К ОТПРАВКЕ EMAIL")
            print(f"{'─' * 60}")

            all_files = {}

            if new_image_path and os.path.exists(new_image_path):
                all_files['latest_image'] = new_image_path
            if old_image_path and os.path.exists(old_image_path):
                all_files['old_image'] = old_image_path

            for file_type, file_path in grid_files.items():
                if file_path and os.path.exists(file_path):
                    all_files[file_type] = file_path

            if 'visualization_path' in comparison:
                viz_path = comparison['visualization_path']
                if viz_path and os.path.exists(viz_path):
                    all_files['comparison_visualization'] = viz_path

            if len(all_files) == 0:
                print("Нет файлов для отправки!")
                return

            print(f"\n{'─' * 60}")
            print("ОТПРАВКА EMAIL СО СЕТКАМИ")
            print(f"{'─' * 60}")

            try:
                grid_count = sum(1 for key in all_files if 'grid' in key.lower())
                subject = f"СЕТОЧНЫЙ АНАЛИЗ ({grid_count} файлов): {territory.get('name', '')} - {change_percentage:.1f}%"

                import inspect

                try:
                    sig = inspect.signature(self.notifier.send_change_notification)
                    params = list(sig.parameters.keys())

                    kwargs = {
                        'territory_info': territory,
                        'change_data': change_data
                    }

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

                    success = self.notifier.send_change_notification(**kwargs)

                    if success:
                        print(f"Email с сетками отправлен!")
                        print(f"   Получатель: {self.email_config.EMAIL_TO}")
                        print(f"   Вложений: {len(all_files)} файлов")
                        print(f"   Изменения: {change_percentage:.1f}%")
                    else:
                        print(f"ОШИБКА отправки email")

                except Exception as sig_error:
                    print(f"Ошибка определения параметров: {sig_error}")

                    success = self.notifier.send_change_notification(
                        territory_info=territory,
                        change_data=change_data
                    )

                    if success:
                        print(f"Базовый email отправлен (без сеток)")
                    else:
                        print(f"Базовый email не отправлен")

            except Exception as email_error:
                print(f"КРИТИЧЕСКАЯ ОШИБКА ПРИ ОТПРАВКЕ EMAIL: {email_error}")
                import traceback
                traceback.print_exc()

            print(f"\n{'─' * 60}")
            print("ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ")
            print(f"{'─' * 60}")

            temp_files_to_clean = []
            for file_type in ['grid_image', 'comparison_grid', 'changes_grid']:
                if file_type in grid_files and grid_files[file_type] and os.path.exists(grid_files[file_type]):
                    temp_files_to_clean.append(grid_files[file_type])

            for file_path in temp_files_to_clean:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as clean_error:
                    print(f"Не удалось удалить {file_path}: {clean_error}")

            print(f"\n{'=' * 60}")
            print("ОТПРАВКА УВЕДОМЛЕНИЯ ЗАВЕРШЕНА")
            print(f"{'=' * 60}")

        except Exception as e:
            print(f"\n{'=' * 60}")
            print(f"КРИТИЧЕСКАЯ ОШИБКА В _send_notification: {e}")
            print(f"{'=' * 60}")
            import traceback
            traceback.print_exc()