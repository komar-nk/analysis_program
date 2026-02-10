# direct_ee_auth.py
import ee

print("Direct Earth Engine authentication...")

# Попробуй напрямую
try:
    ee.Authenticate()  # Откроет браузер или даст ссылку
    ee.Initialize()
    print("✅ Earth Engine authenticated!")
except Exception as e:
    print(f"Error: {e}")
    print("\nManual method:")
    print("1. Open: https://code.earthengine.google.com")
    print("2. Sign up/Sign in")
    print("3. Return and run: python -c 'import ee; ee.Initialize()'")