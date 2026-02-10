import ee
import webbrowser
import os

print("=" * 60)
print("НАСТРОЙКА GOOGLE EARTH ENGINE")
print("=" * 60)

try:
    # Авторизация
    print("\n1. Открываю браузер для авторизации...")
    ee.Authenticate(auth_mode="notebook")

    # Инициализация
    print("\n2. Инициализирую Google Earth Engine...")
    ee.Initialize()

    print("\n НАСТРОЙКА УСПЕШНА!")
    print("\nТеперь можно запускать основную программу:")
    print("python main.py")

except Exception as e:
    print(f"\n Ошибка: {str(e)}")
    print("\nРешения:")
    print("1. Убедитесь, что есть Google аккаунт")
    print("2. Включите интернет")
    print("3. Разрешите доступ к GEE")
    print("4. Если ошибка повторяется, запустите вручную:")
    print("   python -c \"import ee; ee.Authenticate()\"")

input("\nНажмите Enter для выхода...")