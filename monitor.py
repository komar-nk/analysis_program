
"""
Автоматический мониторинг территорий
"""

import schedule
import time
from datetime import datetime
from database import Database
from gee_client import GEEClient
from change_detector import ChangeDetector


def monitor_territory(territory, db, gee, detector):
    """Мониторинг одной территории"""
    print(f"\nТерритория: {territory['name']}")

    # Получаем новое изображение
    success, path, date, message = gee.get_satellite_image(
        territory['latitude'],
        territory['longitude'],
        image_size=512
    )

    if not success:
        print(f"   Ошибка: {message}")
        return False

    print(f"   Снимок от {date}")

    # Анализируем изображение
    analysis = gee.analyze_image(path)

    # Сохраняем в базу
    import os
    file_size = os.path.getsize(path) if os.path.exists(path) else None
    cloud_cover = analysis.get('cloud_cover', {}).get('percentage') if 'error' not in analysis else None

    image_id = db.add_image(
        territory['id'], path, date,
        cloud_cover, file_size
    )

    # Проверяем облачность
    if 'error' not in analysis:
        cloud = analysis['cloud_cover']['percentage']
        print(f"   Облачность: {cloud:.1f}%")

        if cloud > 60:
            print(f"   Высокая облачность")

    # Проверяем изменения
    changes = detector.detect_and_save_changes(territory['id'])
    if changes:
        change_percent = changes['change_percentage']
        print(f"   Изменения: {change_percent:.1f}%")

        if change_percent > 15:
            print(f"   Значительные изменения обнаружены!")

        # Проверяем, отправлено ли email уведомление
        if hasattr(detector, 'email_config') and detector.email_config:
            if detector.email_config.EMAIL_ENABLED and change_percent > detector.email_config.CHANGE_THRESHOLD:
                print(f"   Email уведомление отправлено на {detector.email_config.EMAIL_TO}")

    return True


def daily_monitoring():
    """Ежедневный мониторинг всех территорий"""
    print(f"\n{'=' * 60}")
    print(f"АВТОМАТИЧЕСКИЙ МОНИТОРИНГ - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 60}")

    db = Database()
    gee = GEEClient()
    detector = ChangeDetector(db, gee)

    territories = db.get_all_territories()

    if not territories:
        print("\nНет активных территорий для мониторинга")
        return

    print(f"\nНайдено территорий: {len(territories)}")

    successful = 0
    changes_detected = 0

    for territory in territories:
        if monitor_territory(territory, db, gee, detector):
            successful += 1

    print(f"\n{'=' * 60}")
    print(f"Мониторинг завершен: {successful}/{len(territories)} успешно")
    print(f"Изменений обнаружено: {changes_detected}")

    # Отправляем сводный отчет если есть email уведомления
    if hasattr(detector, 'notifier') and detector.notifier and hasattr(detector, 'email_config'):
        changes_data = db.get_recent_changes(limit=20)
        if changes_data:
            detector.notifier.send_summary_report(changes_data, len(territories))

    print(f"{'=' * 60}")


def schedule_monitoring(hour=10, minute=0):
    """Настройка регулярного мониторинга по расписанию"""
    print(f"\nНастройка расписания...")
    print(f"   Ежедневно в {hour:02d}:{minute:02d}")

    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(daily_monitoring)

    print("\nЗапуск первого мониторинга...")
    daily_monitoring()

    print(f"\nСистема запущена (Ctrl+C для остановки)\n")
    print(f"Email уведомления будут отправляться при изменениях > порога")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nМониторинг остановлен")


def main():
    """Главная функция запуска мониторинга"""
    print("\n" + "=" * 60)
    print("АВТОМАТИЧЕСКИЙ МОНИТОРИНГ ТЕРРИТОРИЙ")
    print("=" * 60)

    print("\nВыберите режим:")
    print("1. Ручной запуск (сейчас)")
    print("2. Автоматический (ежедневно в 10:00)")
    print("3. Автоматический с выбором времени")

    choice = input("\nВаш выбор (1-3): ").strip()

    if choice == '1':
        daily_monitoring()
    elif choice == '2':
        schedule_monitoring(hour=10, minute=0)
    elif choice == '3':
        try:
            hour = int(input("Час (0-23): "))
            minute = int(input("Минута (0-59): "))
            schedule_monitoring(hour=hour, minute=minute)
        except ValueError:
            print("Ошибка: введите числа")
    else:
        print("Неверный выбор")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nВыход")
    except Exception as e:
        print(f"\nОшибка: {e}")