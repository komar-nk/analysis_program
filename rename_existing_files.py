
import os
import shutil
import sqlite3
from pathlib import Path


def transliterate_to_latin(text):
    """Транслитерировать кириллицу в латиницу"""
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
        ' ': '_'
    }

    result = ''
    for char in text:
        if char in translit_dict:
            result += translit_dict[char]
        elif char.isalnum() or char in '_-':
            result += char
        else:
            result += '_'

    # Убираем двойные подчеркивания
    while '__' in result:
        result = result.replace('__', '_')

    return result.strip('_')


def rename_all_files():
    """Переименовать все файлы с кириллицей на латиницу"""
    base_dir = Path("satellite_images")

    # Собираем все файлы
    all_files = []
    for folder in base_dir.rglob("*"):
        if folder.is_dir():
            for file in folder.glob("*.jpg"):
                all_files.append(file)
            for file in folder.glob("*.png"):
                all_files.append(file)

    print(f"Найдено файлов: {len(all_files)}")

    # Подключаем БД
    conn = sqlite3.connect("satellite_monitor.db")
    cursor = conn.cursor()

    renamed_count = 0

    for filepath in all_files:
        old_name = filepath.name
        old_path = str(filepath.absolute())

        # Если есть кириллица
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in old_name)

        if has_cyrillic:
            # Извлекаем части имени
            parts = old_name.split('_')

            if len(parts) >= 3 and parts[0] == 'satellite':
                # Транслитерируем название территории
                territory_part = parts[1]
                transliterated = transliterate_to_latin(territory_part)

                # Собираем новое имя
                new_parts = ['satellite', transliterated] + parts[2:]
                new_name = '_'.join(new_parts)

                # Новый путь
                new_path = str(filepath.parent / new_name)

                try:
                    # Переименовываем файл
                    shutil.move(old_path, new_path)

                    # Обновляем БД
                    cursor.execute("UPDATE images SET image_path = REPLACE(image_path, ?, ?) WHERE image_path LIKE ?",
                                   (old_name, new_name, f"%{old_name}"))

                    renamed_count += 1
                    print(f"✓ {old_name} -> {new_name}")
                except Exception as e:
                    print(f"✗ Ошибка переименования {old_name}: {e}")

    conn.commit()

    # Проверим обновления
    cursor.execute("SELECT COUNT(*) FROM images")
    total_images = cursor.fetchone()[0]

    cursor.execute("SELECT image_path FROM images WHERE image_path LIKE '%╨%'")
    problematic = cursor.fetchall()

    print(f"\n{'=' * 60}")
    print("РЕЗУЛЬТАТ:")
    print(f"{'=' * 60}")
    print(f"Переименовано файлов: {renamed_count}")
    print(f"Всего изображений в БД: {total_images}")
    print(f"Проблемных записей (с кракозябрами): {len(problematic)}")

    if problematic:
        print("\nОстались проблемные записи:")
        for path in problematic:
            print(f"  {path[0]}")

    conn.close()


if __name__ == "__main__":
    rename_all_files()
    input("\nНажмите Enter для выхода...")