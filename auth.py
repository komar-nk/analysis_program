# auth_correct.py
import ee
import os
import subprocess
import sys


def setup_earth_engine():
    print("Setting up Earth Engine...")

    # Проверь есть ли уже креденшиалы
    try:
        ee.Initialize()
        print("✅ Already authenticated!")
        return True
    except:
        print("Need authentication")

    # Способ 1: Проверь service account
    if os.path.exists("credentials.json"):
        print("Found credentials.json, trying service account...")
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "credentials.json"
        try:
            ee.Initialize()
            print("✅ Authenticated via service account")
            return True
        except Exception as e:
            print(f"Service account failed: {e}")

    # Способ 2: Запусти правильную команду gcloud
    print("\nRunning gcloud authentication...")
    cmd = [
        "gcloud", "auth", "application-default", "login",
        "--scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/earthengine,https://www.googleapis.com/auth/devstorage.full_control"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ gcloud authentication successful")
            ee.Initialize()
            print("✅ Earth Engine initialized!")
            return True
        else:
            print(f"gcloud failed: {result.stderr}")
    except Exception as e:
        print(f"Error running gcloud: {e}")

    # Способ 3: Ручная инструкция
    print("\n" + "=" * 60)
    print("MANUAL SETUP REQUIRED")
    print("=" * 60)
    print("\nIf you haven't signed up for Earth Engine:")
    print("1. Go to: https://code.earthengine.google.com")
    print("2. Click 'Sign up' and follow instructions")
    print("3. Wait for approval (24-48 hours)")
    print("\nIf already signed up:")
    print("1. Run this command manually:")
    print(
        "   gcloud auth application-default login --scopes='https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/earthengine'")
    print("2. Then: earthengine authenticate")
    print("3. Finally: python -c 'import ee; ee.Initialize()'")
    print("=" * 60)

    return False


if name == "__main__":
    setup_earth_engine()