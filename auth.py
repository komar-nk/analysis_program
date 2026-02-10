# auth_final.py
import sys
import os

# Monkey patch ДО импорта ee
if sys.version_info[0] == 3:
    import io

    sys.modules['StringIO'] = io

# Проверь существование файла с ключом
key_file = 'credentials.json'
if not os.path.exists(key_file):
    print(f'❌ Файл {key_file} не найден')
    # Поиск других JSON файлов
    for f in os.listdir('.'):
        if f.endswith('.json'):
            print(f'Найден: {f}')
    exit(1)

# Установи переменную окружения
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(key_file)
print(f'✅ Используется файл: {os.environ["GOOGLE_APPLICATION_CREDENTIALS"]}')

# Теперь импортируем ee
try:
    import ee

    ee.Initialize()
    print('✅ Earth Engine успешно инициализирован!')

    # Тестовый запрос
    test_img = ee.Image('LANDSAT/LC08/C01/T1_TOA/LC08_044034_20140318')
    print(f'✅ Тестовый снимок: {test_img.getInfo()["id"]}')

except Exception as e:
    print(f'❌ Ошибка: {e}')