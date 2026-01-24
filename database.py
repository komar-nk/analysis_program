"""
Работа с базой данных территорий (без JSON)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class Database:
    def __init__(self, db_path: str = "satellite_monitor.db"):
        self.db_path = Path(db_path)
        self._init_db()

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
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (territory_id) REFERENCES territories (id),
                    FOREIGN KEY (old_image_id) REFERENCES images (id),
                    FOREIGN KEY (new_image_id) REFERENCES images (id)
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