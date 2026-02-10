import sqlite3
import json

db_path = "satellite_monitor.db"

print("=== ПРОВЕРКА БАЗЫ ДАННЫХ ===")

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Какие таблицы есть
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\n1. Таблицы в базе данных:")
    for table in tables:
        print(f"   - {table['name']}")

    # 2. Проверяем таблицу users
    if 'users' in [t['name'] for t in tables]:
        print("\n2. Таблица users:")
        cursor.execute("PRAGMA table_info(users);")
        columns = cursor.fetchall()
        print("   Структура таблицы users:")
        for col in columns:
            print(f"   - {col['name']} ({col['type']})")

        # Содержимое таблицы users
        cursor.execute("SELECT * FROM users;")
        users = cursor.fetchall()
        print(f"\n   Записей в таблице users: {len(users)}")
        for user in users:
            print(f"\n   Пользователь: {user['username']}")
            if user['notification_emails']:
                try:
                    emails = json.loads(user['notification_emails'])
                    print(f"   Emails: {emails}")
                except:
                    print(f"   Emails (raw): {user['notification_emails']}")
    else:
        print("\n2. Таблица users НЕ СУЩЕСТВУЕТ!")

    # 3. Проверяем таблицу territories
    if 'territories' in [t['name'] for t in tables]:
        cursor.execute("SELECT COUNT(*) as count FROM territories;")
        count = cursor.fetchone()['count']
        print(f"\n3. Территорий в базе: {count}")

    # 4. Проверяем таблицу images
    if 'images' in [t['name'] for t in tables]:
        cursor.execute("SELECT COUNT(*) as count FROM images;")
        count = cursor.fetchone()['count']
        print(f"4. Изображений в базе: {count}")

    conn.close()

except Exception as e:
    print(f"\nОшибка при проверке базы данных: {e}")

input("\nНажмите Enter для выхода...")