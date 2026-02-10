# sync_db_files.py
import os
import sqlite3
from pathlib import Path


def sync_database_with_files():
    """Синхронизировать БД с реальными файлами"""

    # 1. Найти все реальные файлы
    original_dir = Path("satellite_images/original")
    real_files = {}

    if original_dir.exists():
        for file_path in original_dir.glob("*.jpg"):
            real_files[file_path.name.lower()] = str(file_path.absolute())
            print(f"Найден файл: {file_path.name}")

    print(f"\nНайдено реальных файлов: {len(real_files)}")

    # 2. Подключиться к БД
    conn = sqlite3.connect("satellite_monitor.db")
    cursor = conn.cursor()

    # 3. Получить все записи из БД
    cursor.execute("SELECT id, image_path FROM images")
    db_records = cursor.fetchall()

    print(f"\nЗаписей в БД: {len(db_records)}")

    updated_count = 0
    deleted_count = 0

    # 4. Сравнить и обновить
    for img_id, db_path in db_records:
        if not db_path:
            continue

        # Извлекаем имя файла из пути БД
        db_filename = Path(db_path).name
        db_key = db_filename.lower()

        # Ищем соответствующий реальный файл
        if db_key in real_files:
            # Нашли! Обновляем путь
            new_path = real_files[db_key]
            if db_path != new_path:
                cursor.execute("UPDATE images SET image_path = ? WHERE id = ?",
                               (new_path, img_id))
                updated_count += 1
                print(f"✓ Обновлен ID {img_id}: {db_path} -> {new_path}")
        else:
            # Ищем файл с другим регистром или похожим именем
            found_match = False
            for real_key, real_path in real_files.items():
                # Проверяем похожесть имен (игнорируя регистр и небольшие отличия)
                real_name = Path(real_path).name.lower()
                db_name = db_filename.lower()

                # Убираем даты для сравнения
                real_base = "_".join(real_name.split('_')[:-1])
                db_base = "_".join(db_name.split('_')[:-1])

                if real_base == db_base or real_name in db_name or db_name in real_name:
                    cursor.execute("UPDATE images SET image_path = ? WHERE id = ?",
                                   (real_path, img_id))
                    updated_count += 1
                    found_match = True
                    print(f"✓ Найден по совпадению ID {img_id}: {db_path} -> {real_path}")
                    break

            if not found_match:
                # Файл не существует, спрашиваем удалить ли запись
                print(f"\n⚠  Файл не найден для записи БД:")
                print(f"   ID: {img_id}")
                print(f"   Путь в БД: {db_path}")

                # Проверяем есть ли файл в другом месте
                if os.path.exists(db_path):
                    print(f"   Файл существует по указанному пути!")
                else:
                    print(f"   Файл НЕ существует по указанному пути")

                    # Ищем файл с другим именем
                    search_pattern = f"*{img_id}*.jpg"
                    for root, dirs, files in os.walk("."):
                        for file in files:
                            if file.endswith('.jpg') and str(img_id) in file:
                                found_path = os.path.join(root, file)
                                print(f"   Найден возможный файл: {found_path}")
                                update = input(f"   Использовать этот путь? (y/n): ")
                                if update.lower() == 'y':
                                    cursor.execute("UPDATE images SET image_path = ? WHERE id = ?",
                                                   (found_path, img_id))
                                    updated_count += 1
                                    found_match = True
                                    break
                        if found_match:
                            break

    conn.commit()

    # 5. Показать результат
    print(f"\n{'=' * 60}")
    print("РЕЗУЛЬТАТ СИНХРОНИЗАЦИИ:")
    print(f"{'=' * 60}")
    print(f"Обновлено записей: {updated_count}")
    print(f"Удалено записей: {deleted_count}")

    # 6. Проверить все территории
    print(f"\nПРОВЕРКА ТЕРРИТОРИЙ:")
    cursor.execute("""
        SELECT t.id, t.name, COUNT(i.id) as image_count
        FROM territories t
        LEFT JOIN images i ON t.id = i.territory_id
        WHERE t.is_active = 1
        GROUP BY t.id, t.name
    """)

    territories = cursor.fetchall()
    for terr_id, name, count in territories:
        print(f"  {name} (ID: {terr_id}): {count} изображений")

        # Показать файлы для этой территории
        cursor.execute("""
            SELECT id, image_path FROM images 
            WHERE territory_id = ? 
            ORDER BY capture_date DESC
        """, (terr_id,))

        images = cursor.fetchall()
        for img_id, img_path in images:
            exists = "" if os.path.exists(img_path) else ""
            filename = Path(img_path).name if img_path else "Нет пути"
            print(f"    {exists} ID {img_id}: {filename}")

    conn.close()
    print(f"\n Синхронизация завершена!")


if __name__ == "__main__":
    sync_database_with_files()
    input("\nНажмите Enter для выхода...")