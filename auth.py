import os
import ee

# 1. Укажи путь к своему JSON файлу
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/root/analysis_program/credentials.json'

# 2. Инициализация
ee.Initialize()

# 3. Проверка
image = ee.Image('COPERNICUS/S2_SR').first()
print(f'✓ Готово! ID первого снимка: {image.id().getInfo()}')