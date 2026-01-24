import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

load_dotenv()


class EmailConfig:
    """Конфигурация для email уведомлений"""

    def __init__(self):
        # Загружаем настройки из .env или запрашиваем у пользователя
        if os.path.exists('../satellite_monitor/.env'):
            self._load_from_env()
        else:
            self._get_settings_from_user()

    def _load_from_env(self):
        """Загрузка настроек из файла .env"""
        self.EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'False').lower() == 'true'

        if not self.EMAIL_ENABLED:
            print("Email уведомления отключены в файле .env")
            return

        self.SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
        self.EMAIL_FROM = os.getenv('EMAIL_FROM', '')
        self.EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
        self.EMAIL_TO = os.getenv('EMAIL_TO', '')
        self.CHANGE_THRESHOLD = float(os.getenv('CHANGE_THRESHOLD', '5.0'))

        if self.EMAIL_FROM and self.EMAIL_TO and self.EMAIL_PASSWORD:
            print(f"Настройки email загружены из .env файла")
            print(f"   Получатель: {self.EMAIL_TO}")
            print(f"   Порог изменений: {self.CHANGE_THRESHOLD}%")
        else:
            print("Неполные настройки email в .env файле")
            self.EMAIL_ENABLED = False

    def _get_settings_from_user(self):
        """Получение настроек от пользователя"""
        print("\n" + "=" * 60)
        print("НАСТРОЙКА EMAIL УВЕДОМЛЕНИЙ")
        print("=" * 60)

        # Включить уведомления?
        enable = input("\nВключить email уведомления при значительных изменениях? (y/n): ").lower().strip()
        self.EMAIL_ENABLED = (enable == 'y')

        if not self.EMAIL_ENABLED:
            print("Уведомления отключены.")
            return

        # Выбор почтового сервиса
        print("\nВыберите почтовый сервис:")
        print("1. Gmail (рекомендуется)")
        print("2. Яндекс.Почта")
        print("3. Mail.ru")
        print("4. Другой (ввести вручную)")

        choice = input("Ваш выбор (1-4): ").strip()

        if choice == '1':
            self.SMTP_SERVER = "smtp.gmail.com"
            self.SMTP_PORT = 587
            print("\nВНИМАНИЕ для Gmail:")
            print("   Используйте пароль приложения, а не обычный пароль!")
            print("   Как получить пароль приложения:")
            print("   1. Войдите в Google Аккаунт")
            print("   2. Настройки → Безопасность → Двухэтапная аутентификация")
            print("   3. Пароли приложений → Создать пароль")
            print("   4. Выберите 'Почта' и 'Другое (укажите имя)'")
            print("   5. Используйте этот пароль в программе")
        elif choice == '2':
            self.SMTP_SERVER = "smtp.yandex.ru"
            self.SMTP_PORT = 587
            print("\nДля Яндекс:")
            print("   Используйте пароль приложения из Яндекс ID")
        elif choice == '3':
            self.SMTP_SERVER = "smtp.mail.ru"
            self.SMTP_PORT = 587
        else:
            self.SMTP_SERVER = input("SMTP сервер (например: smtp.example.com): ").strip()
            port = input("SMTP порт (обычно 587): ").strip()
            self.SMTP_PORT = int(port) if port else 587

        # Данные для входа
        print("\nВведите данные для отправки писем:")
        self.EMAIL_FROM = input("Email отправителя: ").strip()
        self.EMAIL_PASSWORD = input("Пароль (для Gmail - пароль приложения): ").strip()
        self.EMAIL_TO = input("Email получателя (куда отправлять уведомления): ").strip()

        # Порог для уведомлений
        print("\nНастройка порога изменений:")
        print("   При изменениях выше этого порога будут отправляться уведомления")
        threshold = input("Порог изменений в % (рекомендуется 5-15): ").strip()
        self.CHANGE_THRESHOLD = float(threshold) if threshold else 10.0

        # Тестируем подключение
        print("\nТестируем подключение к почте...")
        if self.test_connection():
            print("Подключение успешно!")

            # Отправляем тестовое письмо
            print("\nОтправляем тестовое письмо...")
            if self.send_test_email():
                print("Тестовое письмо отправлено успешно!")

            # Сохраняем настройки
            save = input("\nСохранить настройки в файл .env? (y/n): ").lower().strip()
            if save == 'y':
                self.save_to_env()
                print("Настройки сохранены в файл .env")
                print("   При следующем запуске они загрузятся автоматически")
        else:
            print("Подключение не удалось, но настройки сохранены в памяти.")
            print("Проверьте данные и настройте заново через меню.")

    def test_connection(self):
        """Тест подключения к SMTP"""
        try:
            print(f"   Сервер: {self.SMTP_SERVER}:{self.SMTP_PORT}")
            print(f"   От: {self.EMAIL_FROM}")
            print(f"   Кому: {self.EMAIL_TO}")

            server = smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT, timeout=10)
            server.starttls()
            server.login(self.EMAIL_FROM, self.EMAIL_PASSWORD)
            server.quit()
            return True

        except Exception as e:
            print(f"Ошибка подключения: {e}")
            print("\nСоветы по устранению:")
            print("1. Проверьте логин и пароль")
            print("2. Для Gmail используйте пароль приложения")
            print("3. Разрешите доступ ненадежным приложениям (если нужно)")
            print("4. Проверьте настройки двухфакторной аутентификации")
            return False

    def send_test_email(self):
        """Отправка тестового письма"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Тест: Система мониторинга настроена"
            msg['From'] = self.EMAIL_FROM
            msg['To'] = self.EMAIL_TO

            html = f"""
            <html>
            <body>
                <h2>Тестовое письмо от системы мониторинга спутниковых снимков</h2>
                <p>Поздравляем! Вы успешно настроили email уведомления.</p>
                <p>Система будет отправлять вам уведомления при обнаружении значительных изменений на отслеживаемых территориях.</p>
                <p><strong>Порог изменений: {self.CHANGE_THRESHOLD}%</strong></p>
                <p>При изменениях выше этого порога вы будете получать уведомления с детальной информацией.</p>
                <p><small>Дата настройки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
                <hr>
                <p><em>Система автоматического мониторинга спутниковых снимков</em></p>
            </body>
            </html>
            """

            text = f"""Тестовое письмо от системы мониторинга спутниковых снимков

Поздравляем! Вы успешно настроили email уведомления.

Система будет отправлять вам уведомления при обнаружении значительных изменений на отслеживаемых территориях.

Порог изменений: {self.CHANGE_THRESHOLD}%

Дата настройки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
Система автоматического мониторинга
"""

            part1 = MIMEText(text, 'plain', 'utf-8')
            part2 = MIMEText(html, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)

            server = smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT)
            server.starttls()
            server.login(self.EMAIL_FROM, self.EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

            print(f"Тестовое письмо отправлено на {self.EMAIL_TO}")
            return True

        except Exception as e:
            print(f"Ошибка отправки тестового письма: {e}")
            return False

    def save_to_env(self):
        """Сохранение настроек в .env файл"""
        import os
        os.makedirs('../satellite_monitor', exist_ok=True)
        with open('../satellite_monitor/.env', 'w') as f:
            f.write(f"EMAIL_ENABLED={self.EMAIL_ENABLED}\n")
            f.write(f"SMTP_SERVER={self.SMTP_SERVER}\n")
            f.write(f"SMTP_PORT={self.SMTP_PORT}\n")
            f.write(f"EMAIL_FROM={self.EMAIL_FROM}\n")
            f.write(f"EMAIL_PASSWORD={self.EMAIL_PASSWORD}\n")
            f.write(f"EMAIL_TO={self.EMAIL_TO}\n")
            f.write(f"CHANGE_THRESHOLD={self.CHANGE_THRESHOLD}\n")
        print("Настройки сохранены в файл .env")


# Функция для быстрой инициализации
def setup_email_notifications():
    """Настройка email уведомлений"""
    config = EmailConfig()
    return config