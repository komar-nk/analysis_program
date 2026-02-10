
import os
import shutil
from pathlib import Path


def setup_directories():
    """Настройка структуры папок проекта"""

    # Создаем необходимые папки
    directories = [
        "satellite_images",  # для кэша изображений
        "changes_results",  # для результатов сравнений
        "archive",  # для архива старых файлов
        "logs"  # для логов
    ]

    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✓ Папка создана/существует: {dir_name}")

    # Перемещаем существующие файлы
    patterns_to_move = [
        "changes_visualization_*.jpg",
        "changes_comparison_*.jpg",
        "fullsize_comparison_*.jpg",
        "temp_comparison_*.jpg",
        "*_result.jpg"
    ]

    files_moved = 0
    for pattern in patterns_to_move:
        for file in Path("../satellite_monitor").glob(pattern):
            if file.is_file():
                dest = Path("../satellite_monitor/changes_results") / file.name
                shutil.move(str(file), str(dest))
                files_moved += 1

    print(f"\nПеремещено файлов в changes_results/: {files_moved}")

    # Обновляем config.py
    config_path = Path("config.py")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "RESULTS_DIR" not in content:
            # Добавляем настройку
            new_line = 'RESULTS_DIR = BASE_DIR / "changes_results"\n'
            if 'CACHE_DIR = BASE_DIR / "satellite_images"' in content:
                content = content.replace(
                    'CACHE_DIR = BASE_DIR / "satellite_images"',
                    'CACHE_DIR = BASE_DIR / "satellite_images"\nRESULTS_DIR = BASE_DIR / "changes_results"'
                )
                print("✓ Обновлён config.py (добавлен RESULTS_DIR)")

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)

    print("\n Настройка завершена!")
    print("   Теперь все файлы изменений будут сохраняться в папке changes_results/")


if __name__ == "__main__":
    setup_directories()