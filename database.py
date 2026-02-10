"""
Работа с базой данных территорий (без JSON)
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class Database:
    def __init__(self, db_path: str = "satellite_monitor.db"):
        self.conn = None
        self.db_path = Path(db_path)
        self._init_db()

    def delete_image(self, image_id):
        """Удалить изображение из базы данных"""
        if self.conn is None:
            print("⚠  Восстанавливаю соединение с БД...")
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS satellite_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    territory_id INTEGER NOT NULL,
                    image_path TEXT NOT NULL,
                    capture_date DATE NOT NULL,
                    cloud_cover REAL,
                    file_size INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()

            cursor.execute('DELETE FROM satellite_images WHERE id = ?', (image_id,))
            self.conn.commit()

            if cursor.rowcount > 0:
                print(f" Изображение ID {image_id} удалено из БД")
                return True
            else:
                print(f" Изображение ID {image_id} не найдено")
                return False

        except Exception as e:
            print(f" Ошибка удаления: {e}")
            return False
        finally:
            cursor.close()

    def cleanup_missing_files(self):
        """Удалить записи о несуществующих файлах"""
        try:
            cursor = self.conn.cursor()

            # Получаем все записи
            cursor.execute('SELECT id, image_path FROM satellite_images')
            all_images = cursor.fetchall()

            deleted_count = 0
            for img in all_images:
                image_id, image_path = img[0], img[1]

                if not os.path.exists(image_path):
                    cursor.execute('DELETE FROM satellite_images WHERE id = ?', (image_id,))
                    cursor.execute('DELETE FROM change_history WHERE image1_id = ? OR image2_id = ?',
                                   (image_id, image_id))
                    deleted_count += 1
                    print(f"🗑️  Удалена запись ID {image_id} (файл отсутствует)")

            self.conn.commit()
            print(f"\n Очистка завершена. Удалено записей: {deleted_count}")
            return deleted_count

        except Exception as e:
            print(f" Ошибка очистки: {e}")
            return 0

    def update_image_size(self, image_id, file_size):
        """Обновить размер файла изображения"""
        if self.conn is None:
            print("⚠  Восстанавливаю соединение с БД...")
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE satellite_images SET file_size = ? WHERE id = ?',
                           (file_size, image_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f" Ошибка обновления размера: {e}")
            return False
        finally:
            cursor.close()

    def get_statistics(self):
        """Получить статистику системы"""
        if self.conn is None:
            print("️  Восстанавливаю соединение с БД...")
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

        stats = {}
        try:
            cursor = self.conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM territories')
            stats['territories'] = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM satellite_images')
            stats['images'] = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM change_history')
            stats['changes'] = cursor.fetchone()[0]

            cursor.execute('SELECT MAX(capture_date) FROM satellite_images')
            stats['last_image_date'] = cursor.fetchone()[0]

            cursor.execute('SELECT MAX(detected_at) FROM change_history')
            stats['last_change_date'] = cursor.fetchone()[0]

            return stats
        except Exception as e:
            print(f" Ошибка статистики: {e}")
            return stats
        finally:
            cursor.close()

    def _init_db(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Таблица территорий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS territories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица изображений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    territory_id INTEGER,
                    image_path TEXT NOT NULL,
                    capture_date TEXT NOT NULL,
                    cloud_cover REAL,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (territory_id) REFERENCES territories (id)
                )
            ''')

            # Таблица изменений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    territory_id INTEGER,
                    old_image_id INTEGER,
                    new_image_id INTEGER,
                    change_percentage REAL,
                    change_data TEXT,  -- НОВЫЙ СТОЛБЕЦ для хранения JSON данных
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    comparison_type TEXT DEFAULT 'auto',  -- НОВЫЙ СТОЛБЕЦ
                    FOREIGN KEY (territory_id) REFERENCES territories (id),
                    FOREIGN KEY (old_image_id) REFERENCES images (id),
                    FOREIGN KEY (new_image_id) REFERENCES images (id)
                )
            ''')

            # таблица пользователей
            cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password TEXT,
                            email TEXT,
                            notification_emails TEXT DEFAULT '[]',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
            conn.commit()

    def add_territory(self, name: str, latitude: float, longitude: float,
                      description: str = "") -> int:
        """Добавление новой территории"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO territories (name, latitude, longitude, description)
                VALUES (?, ?, ?, ?)
            ''', (name, latitude, longitude, description))
            conn.commit()
            return cursor.lastrowid

    def get_territory(self, territory_id: int) -> Optional[Dict[str, Any]]:
        """Получение территории по ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM territories WHERE id = ?', (territory_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_territories(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение всех территорий"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if active_only:
                cursor.execute('SELECT * FROM territories WHERE is_active = 1 ORDER BY name')
            else:
                cursor.execute('SELECT * FROM territories ORDER BY name')

            return [dict(row) for row in cursor.fetchall()]

    def update_territory(self, territory_id: int, **kwargs) -> bool:
        """Обновление территории"""
        if not kwargs:
            return False

        allowed_fields = ['name', 'latitude', 'longitude', 'description', 'is_active']
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            return False

        values.append(territory_id)
        updates.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE territories SET {', '.join(updates)} WHERE id = ?"

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False

    def delete_territory(self, territory_id: int) -> bool:
        """Удаление территории (мягкое удаление)"""
        return self.update_territory(territory_id, is_active=0)

    def add_image(self, territory_id: int, image_path: str, capture_date: str,
                  cloud_cover: Optional[float] = None, file_size: Optional[int] = None) -> int:
        """Добавление изображения в базу"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO images (territory_id, image_path, capture_date, 
                                  cloud_cover, file_size)
                VALUES (?, ?, ?, ?, ?)
            ''', (territory_id, image_path, capture_date, cloud_cover, file_size))
            conn.commit()
            return cursor.lastrowid

    def get_territory_images(self, territory_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение изображений территории"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM images 
                WHERE territory_id = ? 
                ORDER BY capture_date DESC 
                LIMIT ?
            ''', (territory_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_image(self, territory_id: int) -> Optional[Dict[str, Any]]:
        """Получение последнего изображения территории"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM images 
                WHERE territory_id = ? 
                ORDER BY capture_date DESC 
                LIMIT 1
            ''', (territory_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_change(self, territory_id: int, old_image_id: int, new_image_id: int,
                   change_percentage: float) -> int:
        """Добавление записи об изменении"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO changes (territory_id, old_image_id, new_image_id,
                                   change_percentage)
                VALUES (?, ?, ?, ?)
            ''', (territory_id, old_image_id, new_image_id, change_percentage))
            conn.commit()
            return cursor.lastrowid

    def get_recent_changes(self, territory_id: Optional[int] = None,
                           limit: int = 20) -> List[Dict[str, Any]]:
        """Получение последних изменений"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if territory_id:
                cursor.execute('''
                    SELECT c.*, t.name as territory_name 
                    FROM changes c
                    JOIN territories t ON c.territory_id = t.id
                    WHERE c.territory_id = ?
                    ORDER BY c.detected_at DESC 
                    LIMIT ?
                ''', (territory_id, limit))
            else:
                cursor.execute('''
                    SELECT c.*, t.name as territory_name 
                    FROM changes c
                    JOIN territories t ON c.territory_id = t.id
                    ORDER BY c.detected_at DESC 
                    LIMIT ?
                ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Количество территорий
            cursor.execute('SELECT COUNT(*) FROM territories WHERE is_active = 1')
            territory_count = cursor.fetchone()[0]

            # Количество изображений
            cursor.execute('SELECT COUNT(*) FROM images')
            image_count = cursor.fetchone()[0]

            # Количество изменений
            cursor.execute('SELECT COUNT(*) FROM changes')
            change_count = cursor.fetchone()[0]

            # Последняя активность
            cursor.execute('SELECT MAX(created_at) FROM images')
            last_image = cursor.fetchone()[0]

            cursor.execute('SELECT MAX(detected_at) FROM changes')
            last_change = cursor.fetchone()[0]

            return {
                'territories': territory_count,
                'images': image_count,
                'changes': change_count,
                'last_image_date': last_image,
                'last_change_date': last_change
            }

    def get_territory_image_count(self, territory_id: int) -> int:
        """Получение количества изображений для территории"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM images WHERE territory_id = ?', (territory_id,))
            return cursor.fetchone()[0]

    def get_image(self, image_id: int) -> Optional[Dict[str, Any]]:
        """Получение изображения по ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM images WHERE id = ?', (image_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_change_detection(self, territory_id: int, old_image_id: int, new_image_id: int,
                              change_percentage: float, change_data: str,
                              detected_at: str, comparison_type: str = 'auto'):
        """Сохранение результата детекции изменений"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO changes (territory_id, old_image_id, new_image_id,
                                   change_percentage, change_data, detected_at, comparison_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (territory_id, old_image_id, new_image_id, change_percentage,
                  change_data, detected_at, comparison_type))
            conn.commit()
            return cursor.lastrowid

    def save_user_email(self, username: str, email_data: list) -> bool:
        """Сохранение email пользователя в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Проверяем существование пользователя
                cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                user = cursor.fetchone()

                if not user:
                    # Создаем пользователя если его нет
                    cursor.execute('INSERT INTO users (username, notification_emails) VALUES (?, ?)',
                                   (username, json.dumps(email_data)))
                else:
                    # Обновляем email пользователя
                    cursor.execute('UPDATE users SET notification_emails = ? WHERE username = ?',
                                   (json.dumps(email_data), username))

                conn.commit()
                return True

        except Exception as e:
            print(f"Ошибка сохранения email пользователя: {e}")
            return False

    def get_user_emails(self, username: str) -> list:
        """Получение email пользователя из базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute('SELECT notification_emails FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()

                if result and result['notification_emails']:
                    return json.loads(result['notification_emails'])
                return []

        except Exception as e:
            print(f"Ошибка получения email пользователя: {e}")
            return []

    def migrate_users(self):
        """Миграция пользователей из localStorage в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Проверяем, есть ли уже пользователи
                cursor.execute("SELECT COUNT(*) FROM users")
                count = cursor.fetchone()[0]

                if count == 0:
                    print(" Миграция пользователей...")
                    print("   Таблица users пуста, добавляем тестовых пользователей...")

                    import json
                    from datetime import datetime

                    # Тестовые пользователи
                    test_users = [
                        {
                            'username': 'arkadijp308',
                            'emails': [{
                                "address": "arkadijp308@gmail.com",
                                "addedAt": datetime.now().isoformat(),
                                "isPrimary": True,
                                "verified": False
                            }]
                        }
                    ]

                    for user_data in test_users:
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO users (username, notification_emails, created_at)
                                VALUES (?, ?, ?)
                            ''', (
                                user_data['username'],
                                json.dumps(user_data['emails']),
                                datetime.now().isoformat()
                            ))
                            print(f"   ✓ Добавлен пользователь: {user_data['username']}")
                        except Exception as user_error:
                            print(f"   ✗ Ошибка добавления пользователя {user_data['username']}: {user_error}")

                    conn.commit()
                    print(" Миграция пользователей завершена")
                else:
                    print(f"ℹ В таблице users уже есть {count} записей")

        except Exception as e:
            print(f"⚠ Ошибка миграции пользователей: {e}")
            import traceback
            traceback.print_exc()