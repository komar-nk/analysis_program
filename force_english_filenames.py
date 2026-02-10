
import os
import re
import shutil
import sqlite3
from datetime import datetime


def transliterate_to_english(text):
    """Транслитерировать любой текст в английские символы"""
    translit_map = {
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

    result = ''
    for char in text:
        if char in translit_map:
            result += translit_map[char]
        elif char.isalnum():
            result += char
        else:
            result += '_'

    while '__' in result:
        result = result.replace('__', '_')

    return result.strip('_')


def rename_all_images_to_english():
    """Переименовать все изображения в английские имена"""
    print("=" * 60)
    print(" ПЕРЕИМЕНОВАНИЕ ВСЕХ ФАЙЛОВ НА АНГЛИЙСКИЙ")
    print("=" * 60)

    # Папки для поиска
    folders_to_scan = [
        "satellite_images/original",
        "satellite_images/processed",
        "satellite_images/analysis",
        "satellite_images/grid",
        "satellite_images/comparison",
        "satellite_images/changes"
    ]

    # Подключение к БД
    conn = sqlite3.connect("satellite_monitor.db")
    cursor = conn.cursor()

    total_renamed = 0

    for folder in folders_to_scan:
        if not os.path.exists(folder):
            continue

        print(f"\n Папка: {folder}")

        for filename in os.listdir(folder):
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue

            old_path = os.path.join(folder, filename)

            # Проверяем, есть ли кириллица
            has_cyrillic = bool(re.search(r'[а-яА-Я]', filename))

            if has_cyrillic:
                # Оставляем префикс и дату, заменяем только название территории
                if filename.startswith('satellite_'):
                    parts = filename.split('_')
                    if len(parts) >= 3:
                        # Транслитерируем название территории
                        territory_part = '_'.join(parts[1:-2])
                        territory_english = transliterate_to_english(territory_part)

                        # Новое имя с той же датой
                        new_filename = f"satellite_{territory_english}_{parts[-2]}_{parts[-1]}"
                        new_path = os.path.join(folder, new_filename)

                        try:
                            os.rename(old_path, new_path)

                            # Обновляем БД
                            cursor.execute("""
                                UPDATE images 
                                SET image_path = REPLACE(image_path, ?, ?) 
                                WHERE image_path LIKE ?
                            """, (filename, new_filename, f"%{filename}"))

                            total_renamed += 1
                            print(f"   {filename} → {new_filename}")
                        except Exception as e:
                            print(f"   Ошибка: {filename} - {e}")
                else:
                    # Для других файлов просто транслитерируем
                    name_without_ext, ext = filename.rsplit('.', 1)
                    english_name = transliterate_to_english(name_without_ext)
                    new_filename = f"{english_name}.{ext}"
                    new_path = os.path.join(folder, new_filename)

                    try:
                        os.rename(old_path, new_path)
                        total_renamed += 1
                        print(f"   {filename} → {new_filename}")
                    except Exception as e:
                        print(f"   Ошибка: {filename} - {e}")

    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f" Переименовано файлов: {total_renamed}")
    print(f"\n Теперь все файлы имеют английские имена!")


if __name__ == "__main__":
    rename_all_images_to_english()
    input("\nНажмите Enter для выхода...")