"""
Менеджер уведомлений для отправки email с изображениями изменений
Улучшенная версия с обработкой ошибок и гарантированной отправкой
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, Any, Optional, List
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import traceback


class NotificationManager:
    def _create_html_with_grid(self, territory_info, change_data, grid_files):
        """Создание HTML с информацией о сеточном анализе"""
        html = f"""
        <div style="margin: 20px 0; padding: 20px; background: #f0f8ff; border-radius: 10px; border: 2px solid #4CAF50;">
            <h3>📐 АНАЛИЗ ПО КООРДИНАТНОЙ СЕТКЕ 16x16</h3>
            <p><strong>Территория разбита на 256 ячеек для точного анализа</strong></p>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div style="text-align: center;">
                    <h4>🔍 Анализ по ячейкам</h4>
                    <p>Цвет показывает процент изменений в каждой ячейке:</p>
                    <ul style="text-align: left;">
                        <li>🔴 <strong>Красный:</strong> >50% (критические)</li>
                        <li>🟠 <strong>Оранжевый:</strong> 25-50% (высокие)</li>
                        <li>🟡 <strong>Желтый:</strong> 10-25% (средние)</li>
                        <li>🟢 <strong>Зеленый:</strong> <10% (низкие)</li>
                    </ul>
                </div>

                <div style="text-align: center;">
                    <h4>🎯 Преимущества сеточного анализа:</h4>
                    <ul style="text-align: left;">
                        <li>✅ Точно определяет координаты изменений</li>
                        <li>✅ Показывает распределение изменений</li>
                        <li>✅ Фильтрует сезонные изменения</li>
                        <li>✅ Обеспечивает повторяемость измерений</li>
                    </ul>
                </div>
            </div>
        </div>
        """
        return html

    def _send_email_with_grid(self, subject, territory_info, change_data, files_info, html_content):
        """Отправка email с сеточными визуализациями"""
        try:
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = self.config.EMAIL_FROM
            msg['To'] = self.config.EMAIL_TO

            # Текстовая версия
            text_content = self._create_text_content(territory_info, change_data)
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

            # HTML версия с сеткой
            html_full = self._create_html_content(territory_info, change_data, files_info)
            html_full = html_full.replace('</body>', f'{html_content}</body>')
            msg.attach(MIMEText(html_full, 'html', 'utf-8'))

            # Прикрепляем файлы сетки
            attachments_added = self._attach_files(msg, files_info)

            # Отправляем
            return self._send_smtp_email(msg)

        except Exception as e:
            print(f"❌ Ошибка отправки email с сеткой: {e}")
            return False

    def send_notification_with_grid_files(self, territory_info, change_data, grid_files):
        """Упрощенная версия для отправки с сеточными файлами"""
        # Просто передаем все файлы в существующий метод
        return self.send_change_notification(
            territory_info=territory_info,
            change_data=change_data,
            **grid_files  # Распаковываем словарь с файлами
        )
    def send_notification_with_grid(self, territory_info: Dict[str, Any],
                                    change_data: Dict[str, Any],
                                    grid_files: Dict[str, str]) -> bool:
        """
        Отправка уведомления с сеточными визуализациями

        Args:
            territory_info: Информация о территории
            change_data: Данные об изменениях
            grid_files: Словарь с путями к файлам сетки:
                - 'grid_image': основное изображение с сеткой
                - 'grid_analysis': анализ по сетке
                - 'comparison_grid': сравнение с сеткой
                - 'changes_grid': сетка с изменениями

        Returns:
            bool: True если отправка успешна
        """
        print(f"\n📧 ОТПРАВКА УВЕДОМЛЕНИЯ С СЕТКОЙ")

        # Проверяем конфигурацию
        if not self._check_config():
            return False

        # Собираем все файлы для отправки
        all_files = {
            'visualization': change_data.get('visualization_path', ''),
            'comparison': change_data.get('comparison_path', ''),
            'grid_image': grid_files.get('grid_image', ''),
            'grid_analysis': grid_files.get('grid_analysis', ''),
            'comparison_grid': grid_files.get('comparison_grid', ''),
            'changes_grid': grid_files.get('changes_grid', '')
        }

        # Проверяем существование файлов
        files_info = self._collect_files_info(all_files)

        # Создаем тему письма
        subject = f"📐 АНАЛИЗ С СЕТКОЙ: {territory_info.get('name', '')} - {change_data.get('change_percentage', 0):.1f}%"

        # Создаем HTML с описанием сетки
        html_content = self._create_html_with_grid(territory_info, change_data, grid_files)

        # Отправляем email
        return self._send_email_with_grid(subject, territory_info, change_data, files_info, html_content)
    def __init__(self, config=None):
        """
        Инициализация менеджера уведомлений

        Args:
            config: Конфигурация с настройками email
        """
        self.config = config
        self.last_error = None
        self.sent_count = 0

        if config:
            print(f"✓ NotificationManager инициализирован")
            if hasattr(config, 'EMAIL_ENABLED') and config.EMAIL_ENABLED:
                print(f"  Email уведомления: ВКЛЮЧЕНЫ")
                print(f"  Получатель: {config.EMAIL_TO}")
                print(f"  Порог: {config.CHANGE_THRESHOLD}%")
            else:
                print(f"  Email уведомления: ВЫКЛЮЧЕНЫ")
        else:
            print(f"⚠️ NotificationManager: конфиг не предоставлен")

    # ========== ОСНОВНЫЕ ФУНКЦИИ ==========

    def send_change_notification(self, territory_info: Dict[str, Any],
                                 change_data: Dict[str, Any],
                                 latest_image_path: Optional[str] = None,
                                 old_image_path: Optional[str] = None,
                                 grid_image_path: Optional[str] = None,
                                 heatmap_path: Optional[str] = None) -> bool:
        """
        Основная функция отправки уведомлений об изменениях

        Returns:
            bool: True если отправка успешна, False если ошибка
        """
        print(f"\n{'=' * 60}")
        print("📧 ОТПРАВКА УВЕДОМЛЕНИЯ ОБ ИЗМЕНЕНИЯХ")
        print(f"{'=' * 60}")

        # Проверяем конфигурацию
        if not self._check_config():
            return False

        # Проверяем наличие необходимых данных
        if not self._validate_input_data(territory_info, change_data):
            return False

        # Собираем информацию о файлах
        files_info = self._collect_files_info({
            'latest': latest_image_path,
            'old': old_image_path,
            'grid': grid_image_path,
            'heatmap': heatmap_path
        })

        # Создаем сравнительное изображение
        comparison_path = self._create_comparison_image(
            old_image_path, latest_image_path, change_data, territory_info
        )

        if comparison_path:
            files_info['comparison'] = comparison_path

        # Отправляем email
        success = self._send_email_with_attachments(
            territory_info, change_data, files_info
        )

        # Очищаем временные файлы
        self._cleanup_temp_files([comparison_path])

        return success

    def send_advanced_change_notification(self, territory_info: Dict[str, Any],
                                          change_data: Dict[str, Any],
                                          additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Отправка расширенного уведомления с дополнительными данными

        Args:
            territory_info: Информация о территории
            change_data: Данные об изменениях
            additional_data: Дополнительные данные (отчеты, матрицы и т.д.)

        Returns:
            bool: True если отправка успешна
        """
        print(f"\n📨 ОТПРАВКА РАСШИРЕННОГО УВЕДОМЛЕНИЯ")

        if not self._check_config():
            return False

        # Добавляем дополнительную информацию
        if additional_data:
            change_data.update(additional_data)

        # Отправляем уведомление
        return self.send_change_notification(
            territory_info=territory_info,
            change_data=change_data,
            latest_image_path=change_data.get('visualization_path'),
            old_image_path=change_data.get('old_image_path'),
            grid_image_path=change_data.get('grid_image_path'),
            heatmap_path=change_data.get('heatmap_path')
        )

    def send_summary_report(self, changes_data: List[Dict[str, Any]],
                            total_territories: int) -> bool:
        """
        Отправка сводного отчета о мониторинге

        Args:
            changes_data: Список обнаруженных изменений
            total_territories: Общее количество территорий

        Returns:
            bool: True если отправка успешна
        """
        print(f"\n📊 ОТПРАВКА СВОДНОГО ОТЧЕТА")

        if not self._check_config():
            return False

        # Формируем сводку
        summary_text = self._create_summary_text(changes_data, total_territories)

        # Отправляем email
        return self._send_summary_email(summary_text, changes_data, total_territories)

    # ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

    def _check_config(self) -> bool:
        """Проверка конфигурации email"""
        if not self.config:
            print("❌ Ошибка: конфигурация email не предоставлена")
            self.last_error = "Конфигурация email не предоставлена"
            return False

        if not hasattr(self.config, 'EMAIL_ENABLED') or not self.config.EMAIL_ENABLED:
            print("ℹ️ Email уведомления отключены в настройках")
            return False

        required_fields = ['EMAIL_FROM', 'EMAIL_PASSWORD', 'EMAIL_TO',
                           'SMTP_SERVER', 'SMTP_PORT']

        for field in required_fields:
            if not hasattr(self.config, field) or not getattr(self.config, field):
                print(f"❌ Ошибка: не указано поле {field} в конфигурации")
                self.last_error = f"Не указано поле {field} в конфигурации"
                return False

        return True

    def _validate_input_data(self, territory_info: Dict[str, Any],
                             change_data: Dict[str, Any]) -> bool:
        """Проверка входных данных"""
        required_territory = ['name']
        required_change = ['change_percentage']

        # Проверяем обязательные поля территории
        for field in required_territory:
            if field not in territory_info or not territory_info[field]:
                print(f"❌ Ошибка: отсутствует поле территории '{field}'")
                self.last_error = f"Отсутствует поле территории '{field}'"
                return False

        # Проверяем обязательные поля изменений
        for field in required_change:
            if field not in change_data:
                print(f"❌ Ошибка: отсутствует поле изменений '{field}'")
                self.last_error = f"Отсутствует поле изменений '{field}'"
                return False

        # Проверяем процент изменений
        change_percent = change_data.get('change_percentage', 0)
        if not isinstance(change_percent, (int, float)):
            print("❌ Ошибка: процент изменений должен быть числом")
            self.last_error = "Процент изменений должен быть числом"
            return False

        return True

    def _collect_files_info(self, file_paths: Dict[str, str]) -> Dict[str, Dict]:
        """
        Собирает информацию о файлах

        Returns:
            Словарь с информацией о каждом файле
        """
        files_info = {}

        for file_type, file_path in file_paths.items():
            if file_path and os.path.exists(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    files_info[file_type] = {
                        'path': file_path,
                        'size_kb': file_size / 1024,
                        'exists': True,
                        'type': self._get_file_type(file_path)
                    }
                    print(f"  ✅ {file_type}: {file_path} ({file_size / 1024:.1f} KB)")
                except Exception as e:
                    print(f"  ⚠️ Ошибка проверки файла {file_path}: {e}")
            elif file_path:
                print(f"  ❌ {file_type}: файл не существует - {file_path}")

        return files_info

    def _create_comparison_image(self, old_path: Optional[str], new_path: Optional[str],
                                 change_data: Dict[str, Any], territory_info: Dict[str, Any]) -> Optional[str]:
        """
        Создает сравнительное изображение

        Returns:
            Путь к созданному изображению или None в случае ошибки
        """
        if not old_path or not new_path:
            print("  ℹ️ Недостаточно изображений для сравнения")
            return None

        if not os.path.exists(old_path) or not os.path.exists(new_path):
            print("  ⚠️ Один или оба файла не существуют")
            return None

        try:
            print("  🖼️ Создание сравнительного изображения...")

            # Пробуем использовать PIL (более надежно)
            try:
                # Открываем изображения через PIL
                old_img = Image.open(old_path)
                new_img = Image.open(new_path)

                # Приводим к одинаковому размеру
                width = min(old_img.width, new_img.width)
                height = min(old_img.height, new_img.height)

                old_img = old_img.resize((width, height), Image.Resampling.LANCZOS)
                new_img = new_img.resize((width, height), Image.Resampling.LANCZOS)

                # Создаем новое изображение для объединения
                comparison = Image.new('RGB', (width * 2, height + 60), (40, 40, 40))

                # Добавляем изображения
                comparison.paste(old_img, (0, 60))
                comparison.paste(new_img, (width, 60))

                # Добавляем текст
                draw = ImageDraw.Draw(comparison)

                # Пробуем разные шрифты
                fonts_to_try = [
                    ("arial.ttf", 20),
                    ("DejaVuSans.ttf", 20),
                    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                ]

                font = None
                for font_path, font_size in fonts_to_try:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except:
                        continue

                if font is None:
                    font = ImageFont.load_default()

                # Добавляем подписи
                change_percent = change_data.get('change_percentage', 0)
                territory_name = territory_info.get('name', 'Неизвестная территория')

                draw.text((10, 10), "СТАРЫЙ СНИМОК", fill=(255, 255, 255), font=font)
                draw.text((width + 10, 10), "НОВЫЙ СНИМОК", fill=(255, 255, 255), font=font)
                draw.text((10, 35), f"Изменения: {change_percent:.1f}%",
                          fill=(255, 255, 150), font=font)
                draw.text((width - 200, 35), territory_name,
                          fill=(200, 255, 200), font=font)

                # Добавляем даты
                old_date = change_data.get('old_image_date', '')
                new_date = change_data.get('new_image_date', '')

                if old_date:
                    draw.text((10, height + 40), f"Дата: {old_date}",
                              fill=(200, 200, 255), font=font)
                if new_date:
                    draw.text((width + 10, height + 40), f"Дата: {new_date}",
                              fill=(200, 200, 255), font=font)

                # Сохраняем
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                comparison_path = f"comparison_{timestamp}.jpg"
                comparison.save(comparison_path, 'JPEG', quality=85, optimize=True)

                print(f"  ✅ Сравнение создано: {comparison_path}")
                return comparison_path

            except Exception as pil_error:
                print(f"  ⚠️ Ошибка PIL: {pil_error}")
                # Пробуем OpenCV как запасной вариант
                return self._create_comparison_opencv(old_path, new_path, change_data, territory_info)

        except Exception as e:
            print(f"  ❌ Ошибка создания сравнения: {e}")
            return None

    def _create_comparison_opencv(self, old_path: str, new_path: str,
                                  change_data: Dict[str, Any], territory_info: Dict[str, Any]) -> Optional[str]:
        """Создание сравнения через OpenCV"""
        try:
            old_img = cv2.imread(old_path)
            new_img = cv2.imread(new_path)

            if old_img is None or new_img is None:
                return None

            # Приводим к одинаковому размеру
            height = min(old_img.shape[0], new_img.shape[0])
            width = min(old_img.shape[1], new_img.shape[1])

            old_img = cv2.resize(old_img, (width, height))
            new_img = cv2.resize(new_img, (width, height))

            # Создаем подложку
            comparison = np.zeros((height + 60, width * 2, 3), dtype=np.uint8)
            comparison.fill(40)

            # Добавляем изображения
            comparison[60:, :width] = old_img
            comparison[60:, width:] = new_img

            # Добавляем текст
            font = cv2.FONT_HERSHEY_SIMPLEX
            change_percent = change_data.get('change_percentage', 0)

            cv2.putText(comparison, "СТАРЫЙ СНИМОК", (10, 25),
                        font, 0.7, (255, 255, 255), 2)
            cv2.putText(comparison, "НОВЫЙ СНИМОК", (width + 10, 25),
                        font, 0.7, (255, 255, 255), 2)
            cv2.putText(comparison, f"Изменения: {change_percent:.1f}%",
                        (10, 50), font, 0.7, (255, 255, 150), 2)

            territory_name = territory_info.get('name', '')
            if territory_name:
                name_x = width - cv2.getTextSize(territory_name, font, 0.6, 2)[0][0] - 10
                cv2.putText(comparison, territory_name, (name_x, 50),
                            font, 0.6, (200, 255, 200), 2)

            # Добавляем даты
            old_date = change_data.get('old_image_date', '')
            new_date = change_data.get('new_image_date', '')

            if old_date:
                cv2.putText(comparison, old_date, (10, height + 45),
                            font, 0.5, (200, 200, 255), 1)
            if new_date:
                cv2.putText(comparison, new_date, (width + 10, height + 45),
                            font, 0.5, (200, 200, 255), 1)

            # Сохраняем
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            comparison_path = f"comparison_opencv_{timestamp}.jpg"
            cv2.imwrite(comparison_path, comparison)

            print(f"  ✅ Сравнение создано (OpenCV): {comparison_path}")
            return comparison_path

        except Exception as e:
            print(f"  ❌ Ошибка OpenCV: {e}")
            return None

    def _get_file_type(self, file_path: str) -> str:
        """Определяет тип файла по расширению"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return 'image'
        elif ext in ['.pdf', '.doc', '.docx']:
            return 'document'
        elif ext in ['.json', '.txt', '.csv']:
            return 'data'
        else:
            return 'other'

    # ========== EMAIL ФУНКЦИИ ==========

    def _send_email_with_attachments(self, territory_info: Dict[str, Any],
                                     change_data: Dict[str, Any],
                                     files_info: Dict[str, Dict]) -> bool:
        """Отправка email с вложениями"""
        try:
            print("\n✉️ ПОДГОТОВКА EMAIL...")

            # Создаем тему письма
            subject = self._create_email_subject(territory_info, change_data)

            # Создаем сообщение
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = self.config.EMAIL_FROM
            msg['To'] = self.config.EMAIL_TO

            # Добавляем текстовую и HTML версии
            text_content = self._create_text_content(territory_info, change_data)
            html_content = self._create_html_content(territory_info, change_data, files_info)

            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Прикрепляем файлы
            attachments_added = self._attach_files(msg, files_info)

            print(f"  📎 Прикреплено файлов: {attachments_added}")

            # Отправляем email
            return self._send_smtp_email(msg)

        except Exception as e:
            print(f"❌ Ошибка подготовки email: {e}")
            traceback.print_exc()
            self.last_error = str(e)
            return False

    def _create_email_subject(self, territory_info: Dict[str, Any],
                              change_data: Dict[str, Any]) -> str:
        """Создание темы письма"""
        change_percent = change_data.get('change_percentage', 0)
        territory_name = territory_info.get('name', 'Территория')

        # Определяем эмодзи и уровень в зависимости от процента изменений
        if change_percent > 50:
            emoji = "🚨🚨🚨"
            level = "КРИТИЧЕСКИЙ"
        elif change_percent > 20:
            emoji = "🚨🚨"
            level = "ВЫСОКИЙ"
        elif change_percent > 10:
            emoji = "🚨"
            level = "СРЕДНИЙ"
        elif change_percent > 5:
            emoji = "⚠️"
            level = "НИЗКИЙ"
        else:
            emoji = "ℹ️"
            level = "МИНИМАЛЬНЫЙ"

        # Проверяем сезонность
        is_seasonal = change_data.get('is_seasonal', False)
        if is_seasonal:
            return f"{emoji} [СЕЗОННЫЕ] {level} изменения на {territory_name} - {change_percent:.1f}%"
        else:
            return f"{emoji} {level} изменения на {territory_name} - {change_percent:.1f}%"

    def _create_text_content(self, territory_info: Dict[str, Any],
                             change_data: Dict[str, Any]) -> str:
        """Создание текстового содержимого письма"""
        change_percent = change_data.get('change_percentage', 0)
        territory_name = territory_info.get('name', 'Неизвестная территория')
        lat = territory_info.get('latitude', 0)
        lon = territory_info.get('longitude', 0)

        text = f"""
{'=' * 60}
🚨 ОБНАРУЖЕНЫ ИЗМЕНЕНИЯ НА ТЕРРИТОРИИ
{'=' * 60}

📌 ТЕРРИТОРИЯ:
Название: {territory_name}
Координаты: {lat:.6f}, {lon:.6f}

📊 ИЗМЕНЕНИЯ:
Процент изменений: {change_percent:.1f}%
Уровень: {change_data.get('change_level', 'Неизвестно')}

📅 ДАТЫ СНИМКОВ:
Старый: {change_data.get('old_image_date', 'Неизвестно')}
Новый: {change_data.get('new_image_date', 'Неизвестно')}

⏰ ВРЕМЯ АНАЛИЗА:
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📎 ВЛОЖЕНИЯ:
В письмо прикреплены изображения с изменениями.

{'=' * 60}
Система автоматического мониторинга территорий
Школа №2031, Москва
{'=' * 60}
"""
        return text

    def _create_html_content(self, territory_info: Dict[str, Any],
                             change_data: Dict[str, Any],
                             files_info: Dict[str, Dict]) -> str:
        """Создание HTML содержимого письма"""
        change_percent = change_data.get('change_percentage', 0)
        territory_name = territory_info.get('name', 'Неизвестная территория')

        # Определяем цвет в зависимости от уровня изменений
        if change_percent > 50:
            color = "#ff4444"
            bg_color = "#ffeaea"
            header_text = "🚨 КРИТИЧЕСКИЕ ИЗМЕНЕНИЯ"
        elif change_percent > 20:
            color = "#ff8800"
            bg_color = "#fff4e6"
            header_text = "⚠️ ЗНАЧИТЕЛЬНЫЕ ИЗМЕНЕНИЯ"
        elif change_percent > 10:
            color = "#44aa44"
            bg_color = "#eaffea"
            header_text = "📊 ЗАМЕТНЫЕ ИЗМЕНЕНИЯ"
        else:
            color = "#4444ff"
            bg_color = "#eaeaff"
            header_text = "ℹ️ ИЗМЕНЕНИЯ"

        # Создаем список вложений
        attachments_list = ""
        for file_type, file_info in files_info.items():
            # Проверяем, что file_info это словарь
            if isinstance(file_info, dict) and file_info.get('exists'):
                size = file_info.get('size_kb', 0)
                attachments_list += f"<li>{file_type}: {size:.1f} KB</li>"
            elif isinstance(file_info, str) and os.path.exists(file_info):
                # Если передали просто путь как строку
                try:
                    size = os.path.getsize(file_info) / 1024
                    attachments_list += f"<li>{file_type}: {size:.1f} KB</li>"
                except:
                    attachments_list += f"<li>{file_type}</li>"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, {color}, {color}dd);
            color: white;
            padding: 25px;
            border-radius: 10px 10px 0 0;
            margin: -30px -30px 30px -30px;
            text-align: center;
        }}
        .info-box {{
            background: {bg_color};
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 5px solid {color};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .percentage {{
            font-size: 24px;
            font-weight: bold;
            color: {color};
            text-align: center;
            margin: 20px 0;
        }}
        .badge {{
            background: {color};
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
            margin: 5px;
        }}
        .attachments {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{header_text}</h1>
            <h2>{territory_name}</h2>
        </div>

        <div class="percentage">
            {change_percent:.1f}% изменений
        </div>

        <div class="info-box">
            <h3>📋 Информация о территории</h3>
            <table>
                <tr>
                    <th>Параметр</th>
                    <th>Значение</th>
                </tr>
                <tr>
                    <td>Название</td>
                    <td>{territory_name}</td>
                </tr>
                <tr>
                    <td>Координаты</td>
                    <td>{territory_info.get('latitude', 'N/A'):.6f}, {territory_info.get('longitude', 'N/A'):.6f}</td>
                </tr>
                <tr>
                    <td>Описание</td>
                    <td>{territory_info.get('description', 'Не указано')}</td>
                </tr>
            </table>
        </div>

        <div class="info-box">
            <h3>📊 Детали изменений</h3>
            <table>
                <tr>
                    <th>Параметр</th>
                    <th>Значение</th>
                </tr>
                <tr>
                    <td>Процент изменений</td>
                    <td><span class="badge">{change_percent:.1f}%</span></td>
                </tr>
                <tr>
                    <td>Уровень</td>
                    <td>{change_data.get('change_level', 'Неизвестно')}</td>
                </tr>
                <tr>
                    <td>Дата старого снимка</td>
                    <td>{change_data.get('old_image_date', 'Неизвестно')}</td>
                </tr>
                <tr>
                    <td>Дата нового снимка</td>
                    <td>{change_data.get('new_image_date', 'Неизвестно')}</td>
                </tr>
                <tr>
                    <td>Время обнаружения</td>
                    <td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
        </div>

        <div class="attachments">
            <h3>📎 Вложения</h3>
            <ul>
                {attachments_list}
            </ul>
        </div>

        <div class="footer">
            <p>🚨 Это автоматическое уведомление системы мониторинга территорий</p>
            <p>📊 Система разработана для школы №2031, Москва</p>
            <p>📅 Дата отправки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _attach_files(self, msg: MIMEMultipart, files_info: Dict[str, Dict]) -> int:
        """Прикрепление файлов к email"""
        attachments_added = 0

        for file_type, info in files_info.items():
            # Определяем путь к файлу
            if isinstance(info, dict):
                if not info.get('exists'):
                    continue
                file_path = info.get('path', '')
            elif isinstance(info, str):
                file_path = info
            else:
                continue

            if not file_path or not os.path.exists(file_path):
                continue

            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()

                # Определяем тип файла
                ext = os.path.splitext(file_path)[1].lower()

                if ext in ['.jpg', '.jpeg']:
                    img = MIMEImage(file_data, name=os.path.basename(file_path))
                    img.add_header('Content-Disposition', 'attachment',
                                   filename=os.path.basename(file_path))
                    msg.attach(img)
                    attachments_added += 1

                elif ext in ['.png', '.bmp', '.gif']:
                    img = MIMEImage(file_data)
                    img.add_header('Content-Disposition', 'attachment',
                                   filename=os.path.basename(file_path))
                    msg.attach(img)
                    attachments_added += 1

                else:
                    # Общий тип файла
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment',
                                    filename=os.path.basename(file_path))
                    msg.attach(part)
                    attachments_added += 1

            except Exception as e:
                print(f"  ⚠️ Ошибка прикрепления файла {file_path}: {e}")

        return attachments_added

    def _send_smtp_email(self, msg: MIMEMultipart) -> bool:
        """Отправка email через SMTP"""
        try:
            print(f"  🔗 Подключение к SMTP серверу...")
            print(f"  Сервер: {self.config.SMTP_SERVER}:{self.config.SMTP_PORT}")

            # Создаем SMTP соединение
            server = smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT, timeout=30)

            # Включаем TLS если нужно
            if self.config.SMTP_PORT == 587:
                server.starttls()
                print("  🔐 TLS включен")

            # Логинимся
            print(f"  🔑 Авторизация...")
            server.login(self.config.EMAIL_FROM, self.config.EMAIL_PASSWORD)

            # Отправляем письмо
            print(f"  📤 Отправка письма...")
            server.send_message(msg)

            # Закрываем соединение
            server.quit()

            print(f"  ✅ Email успешно отправлен!")
            print(f"     Тема: {msg['Subject']}")
            print(f"     Кому: {self.config.EMAIL_TO}")

            self.sent_count += 1
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ Ошибка аутентификации: неверный логин или пароль")
            self.last_error = "Ошибка аутентификации SMTP"
            return False

        except smtplib.SMTPConnectError:
            print("❌ Ошибка подключения к SMTP серверу")
            self.last_error = "Ошибка подключения к SMTP серверу"
            return False

        except smtplib.SMTPException as e:
            print(f"❌ Ошибка SMTP: {e}")
            self.last_error = f"Ошибка SMTP: {str(e)}"
            return False

        except Exception as e:
            print(f"❌ Неожиданная ошибка при отправке email: {e}")
            traceback.print_exc()
            self.last_error = str(e)
            return False

    def _send_summary_email(self, summary_text: str,
                            changes_data: List[Dict[str, Any]],
                            total_territories: int) -> bool:
        """Отправка сводного email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📊 Сводный отчет мониторинга - {datetime.now().strftime('%Y-%m-%d')}"
            msg['From'] = self.config.EMAIL_FROM
            msg['To'] = self.config.EMAIL_TO

            # Текстовая версия
            text_content = summary_text
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

            # HTML версия
            html_content = self._create_summary_html(changes_data, total_territories)
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Отправляем
            return self._send_smtp_email(msg)

        except Exception as e:
            print(f"❌ Ошибка отправки сводного отчета: {e}")
            self.last_error = str(e)
            return False

    def _create_summary_text(self, changes_data: List[Dict[str, Any]],
                             total_territories: int) -> str:
        """Создание текста сводного отчета"""
        detected_changes = len(changes_data)
        date_str = datetime.now().strftime('%Y-%m-%d')

        text = f"""
{'=' * 60}
📊 СВОДНЫЙ ОТЧЕТ МОНИТОРИНГА
{'=' * 60}

📅 Дата: {date_str}
🏞️ Территории: {total_territories}
🔍 Обнаружено изменений: {detected_changes}

{'=' * 60}
ДЕТАЛИ ИЗМЕНЕНИЙ:
{'=' * 60}
"""

        if detected_changes > 0:
            for i, change in enumerate(changes_data[:10], 1):
                territory = change.get('territory_name', 'Неизвестно')
                percent = change.get('change_percentage', 0)
                date = change.get('detected_at', '')

                text += f"\n{i}. {territory}"
                text += f"\n   📊 Изменения: {percent:.1f}%"
                text += f"\n   ⏰ Обнаружено: {date}"
                text += f"\n   {'─' * 40}"
        else:
            text += "\nℹ️ Изменений не обнаружено"

        text += f"""
{'=' * 60}
Система автоматического мониторинга территорий
Школа №2031, Москва
{'=' * 60}
"""

        return text

    def _create_summary_html(self, changes_data: List[Dict[str, Any]],
                             total_territories: int) -> str:
        """Создание HTML сводного отчета"""
        detected_changes = len(changes_data)
        date_str = datetime.now().strftime('%Y-%m-%d')

        # Создаем строки таблицы
        table_rows = ""
        if detected_changes > 0:
            for change in changes_data[:10]:
                territory = change.get('territory_name', 'Неизвестно')
                percent = change.get('change_percentage', 0)
                date = change.get('detected_at', '')

                # Определяем цвет строки в зависимости от процента изменений
                row_color = "#ffeaea" if percent > 20 else "#eaffea" if percent > 5 else "#f9f9f9"

                table_rows += f"""
                <tr style="background: {row_color};">
                    <td>{territory}</td>
                    <td><strong>{percent:.1f}%</strong></td>
                    <td>{date}</td>
                </tr>
                """
        else:
            table_rows = """
            <tr>
                <td colspan="3" style="text-align: center; color: #666;">
                    ℹ️ Изменений не обнаружено
                </td>
            </tr>
            """

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .header {{ background: #4CAF50; color: white; padding: 20px; border-radius: 5px; }}
        .stats {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Сводный отчет мониторинга</h1>
            <h2>{date_str}</h2>
        </div>

        <div class="stats">
            <h3>📈 Статистика</h3>
            <p>🏞️ Территории: {total_territories}</p>
            <p>🔍 Обнаружено изменений: {detected_changes}</p>
        </div>

        <h3>📋 Детали изменений</h3>
        <table>
            <tr>
                <th>Территория</th>
                <th>Изменения</th>
                <th>Время обнаружения</th>
            </tr>
            {table_rows}
        </table>

        <div style="margin-top: 30px; padding: 15px; background: #f5f5f5; border-radius: 5px;">
            <p>📅 Дата отчета: {date_str}</p>
            <p>🏫 Система мониторинга территорий, Школа №2031, Москва</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _cleanup_temp_files(self, file_paths: List[Optional[str]]):
        """Очистка временных файлов"""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"  🗑️  Удален временный файл: {file_path}")
                except Exception as e:
                    print(f"  ⚠️  Не удалось удалить файл {file_path}: {e}")

    # ========== СТАТИСТИКА И ИНФОРМАЦИЯ ==========

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики отправленных уведомлений"""
        return {
            'sent_count': self.sent_count,
            'last_error': self.last_error,
            'config_exists': self.config is not None,
            'email_enabled': self.config.EMAIL_ENABLED if self.config else False
        }

    def test_connection(self) -> bool:
        """Тестирование подключения к SMTP серверу"""
        if not self._check_config():
            return False

        try:
            print(f"\n🔍 ТЕСТ ПОДКЛЮЧЕНИЯ К SMTP...")
            print(f"  Сервер: {self.config.SMTP_SERVER}:{self.config.SMTP_PORT}")

            server = smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT, timeout=10)

            if self.config.SMTP_PORT == 587:
                server.starttls()

            server.login(self.config.EMAIL_FROM, self.config.EMAIL_PASSWORD)
            server.quit()

            print(f"  ✅ Подключение успешно!")
            return True

        except Exception as e:
            print(f"  ❌ Ошибка подключения: {e}")
            self.last_error = str(e)
            return False

    def _create_html_with_grid(self, territory_info, change_data, grid_files):
        pass

    def _send_email_with_grid(self, subject, territory_info, change_data, files_info, html_content):
        pass


# ========== КОНФИГУРАЦИОННЫЙ КЛАСС ==========

class EmailConfig:
    """Класс для хранения конфигурации email"""

    def __init__(self, dotenv_file: str = '.env'):
        """
        Загрузка конфигурации из .env файла

        Args:
            dotenv_file: Путь к файлу .env
        """
        self._load_from_env(dotenv_file)

    def _load_from_env(self, dotenv_file: str):
        """Загрузка настроек из .env файла"""
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_file)

            self.EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'False').lower() == 'true'
            self.SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            self.SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
            self.EMAIL_FROM = os.getenv('EMAIL_FROM', '')
            self.EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
            self.EMAIL_TO = os.getenv('EMAIL_TO', '')
            self.CHANGE_THRESHOLD = float(os.getenv('CHANGE_THRESHOLD', '5.0'))

            print(f"✓ Конфигурация email загружена из {dotenv_file}")

            if self.EMAIL_ENABLED:
                print(f"  ✅ Уведомления ВКЛЮЧЕНЫ")
                print(f"  📧 От: {self.EMAIL_FROM}")
                print(f"  📧 Кому: {self.EMAIL_TO}")
                print(f"  📊 Порог: {self.CHANGE_THRESHOLD}%")
            else:
                print(f"  ⚠️  Уведомления ВЫКЛЮЧЕНЫ")

        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            # Устанавливаем значения по умолчанию
            self.EMAIL_ENABLED = False
            self.SMTP_SERVER = 'smtp.gmail.com'
            self.SMTP_PORT = 587
            self.EMAIL_FROM = ''
            self.EMAIL_PASSWORD = ''
            self.EMAIL_TO = ''
            self.CHANGE_THRESHOLD = 5.0


# ========== ПРОСТАЯ ВЕРСИЯ ДЛЯ СОВМЕСТИМОСТИ ==========
def send_change_notification_with_grid(self, territory_info: Dict[str, Any],
                                       change_data: Dict[str, Any],
                                       grid_files: Dict[str, str]) -> bool:
    """
    Отправка уведомления с сеточными визуализациями
    """
    print(f"\n📧 ОТПРАВКА УВЕДОМЛЕНИЯ С СЕТКОЙ")

    # Основные файлы
    files_info = {
        'latest': change_data.get('latest_image_path'),
        'old': change_data.get('old_image_path'),
        'comparison': change_data.get('comparison_path')
    }

    # Добавляем сеточные файлы
    if 'grid_visualization' in grid_files:
        files_info['grid_analysis'] = grid_files['grid_visualization']
    if 'grid_image' in grid_files:
        files_info['grid_original'] = grid_files['grid_image']
    if 'comparison_grid' in grid_files:
        files_info['grid_comparison'] = grid_files['comparison_grid']

    # Создаем HTML с сеткой
    html_content = self._create_html_with_grid(territory_info, change_data, grid_files)

    # Отправляем
    return self._send_email_with_grid(territory_info, change_data, files_info, html_content)


def _create_html_with_grid(self, territory_info, change_data, grid_files):
    """HTML с информацией о сетке"""
    html = f"""
    <div style="margin: 20px 0; padding: 15px; background: #f0f8ff; border-radius: 10px;">
        <h3>📐 АНАЛИЗ ПО КООРДИНАТНОЙ СЕТКЕ</h3>
        <p>Территория разбита на сетку 16x16 ячеек для точного анализа</p>

        <div style="display: flex; gap: 10px; margin: 15px 0;">
            <div style="flex: 1; text-align: center;">
                <h4>🔍 Анализ по ячейкам</h4>
                <p>Каждая ячейка анализируется отдельно</p>
                <img src="cid:grid_analysis" style="width: 100%; border: 2px solid #ccc; border-radius: 5px;">
            </div>

            <div style="flex: 1; text-align: center;">
                <h4>🔄 Сравнение</h4>
                <p>Сетка наложена на оба снимка</p>
                <img src="cid:grid_comparison" style="width: 100%; border: 2px solid #ccc; border-radius: 5px;">
            </div>
        </div>

        <div style="background: #e6f7ff; padding: 10px; border-radius: 5px;">
            <h4>🎨 Легенда цветов сетки:</h4>
            <ul style="list-style: none; padding: 0;">
                <li>🔴 <strong>Красный:</strong> >50% изменений (критические)</li>
                <li>🟠 <strong>Оранжевый:</strong> 25-50% изменений (высокие)</li>
                <li>🟡 <strong>Желтый:</strong> 10-25% изменений (средние)</li>
                <li>🟢 <strong>Зеленый:</strong> <10% изменений (низкие)</li>
            </ul>
        </div>
    </div>
    """
    return html
def send_simple_notification(territory_info: Dict[str, Any],
                             change_data: Dict[str, Any],
                             config: Any = None) -> bool:
    """
    Простая функция для отправки уведомления (для обратной совместимости)

    Args:
        territory_info: Информация о территории
        change_data: Данные об изменениях
        config: Конфигурация email (опционально)

    Returns:
        bool: True если отправка успешна
    """
    try:
        if config is None:
            # Пробуем создать конфиг
            try:
                config = EmailConfig()
            except:
                print("❌ Не удалось загрузить конфигурацию email")
                return False

        notifier = NotificationManager(config)
        return notifier.send_change_notification(territory_info, change_data)

    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        return False


# ========== ТЕСТИРОВАНИЕ ==========

if __name__ == "__main__":
    print("🔧 ТЕСТИРОВАНИЕ NOTIFICATION MANAGER")
    print("=" * 50)

    # Создаем конфигурацию
    config = EmailConfig()

    if not config.EMAIL_ENABLED or not config.EMAIL_FROM or not config.EMAIL_PASSWORD:
        print("❌ Конфигурация email не настроена")
        print("   Заполните файл .env с настройками email")
        exit(1)

    # Создаем менеджер уведомлений
    notifier = NotificationManager(config)

    # Тестируем подключение
    print("\n1. Тестирование подключения к SMTP...")
    if notifier.test_connection():
        print("   ✅ Подключение успешно")
    else:
        print("   ❌ Не удалось подключиться")
        exit(1)

    # Тестовые данные
    print("\n2. Подготовка тестовых данных...")
    territory_info = {
        "name": "Тестовая территория",
        "latitude": 55.7558,
        "longitude": 37.6176,
        "description": "Тестовый полигон для проверки системы"
    }

    change_data = {
        "change_percentage": 12.5,
        "change_level": "средний",
        "old_image_date": "2024-01-15",
        "new_image_date": "2024-02-15",
        "significance": "Обнаружены заметные изменения"
    }

    # Создаем тестовые изображения
    import numpy as np

    test_images = []
    for i, name in enumerate(['test_old.jpg', 'test_new.jpg']):
        img = np.random.randint(100, 200, (300, 400, 3), dtype=np.uint8)
        cv2.imwrite(name, img)
        test_images.append(name)
        print(f"   ✅ Создано: {name}")

    # Тестируем отправку уведомления
    print("\n3. Тестирование отправки уведомления...")
    success = notifier.send_change_notification(
        territory_info=territory_info,
        change_data=change_data,
        latest_image_path=test_images[1],
        old_image_path=test_images[0]
    )

    # Очищаем тестовые файлы
    print("\n4. Очистка тестовых файлов...")
    for img in test_images:
        if os.path.exists(img):
            os.remove(img)
            print(f"   ✅ Удален: {img}")

    # Выводим статистику
    print("\n5. Статистика:")
    stats = notifier.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    if success:
        print("\n🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
    else:
        print("\n❌ ТЕСТ НЕ ПРОЙДЕН")

    print("\n" + "=" * 50)