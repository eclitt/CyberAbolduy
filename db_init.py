import sqlite3
import datetime
from typing import List, Tuple, Optional

class StudentDB:
    def __init__(self, db_name='students.db'):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        """Создает соединение с базой данных"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        return conn
    
    def init_database(self):
        """Инициализирует таблицы базы данных"""
        with self.get_connection() as conn:
            # Таблица студентов
            conn.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    user_id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    group_name TEXT DEFAULT 'Не указана'
                )
            ''')
            
            # Таблица текущих на паре (активная сессия)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS current_class (
                    user_id TEXT PRIMARY KEY,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES students (user_id)
                )
            ''')
            
            conn.commit()
    
    def add_student(self, user_id: str, full_name: str, group_name: str = 'Не указана') -> bool:
        """Добавляет нового студента"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    'INSERT INTO students (user_id, full_name, group_name) VALUES (?, ?, ?)',
                    (user_id, full_name, group_name)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Пользователь уже существует
        except Exception as e:
            print(f"Ошибка добавления студента: {e}")
            return False
    
    def get_student(self, user_id: str) -> Optional[sqlite3.Row]:
        """Получает данные студента по ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM students WHERE user_id = ?', 
                (user_id,)
            )
            return cursor.fetchone()
    
    def get_all_students(self) -> List[sqlite3.Row]:
        """Получает список всех студентов"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM students ORDER BY full_name'
            )
            return cursor.fetchall()
    
    def mark_attendance(self, user_id: str) -> bool:
        """Отмечает студента на паре"""
        try:
            with self.get_connection() as conn:
                # Добавляем в текущую пару
                conn.execute(
                    'INSERT OR REPLACE INTO current_class (user_id) VALUES (?)',
                    (user_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка отметки посещения: {e}")
            return False
    
    def remove_attendance(self, user_id: str) -> bool:
        """Удаляет студента из текущей пары"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    'DELETE FROM current_class WHERE user_id = ?',
                    (user_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления из пары: {e}")
            return False
    
    def get_current_attendance(self) -> List[sqlite3.Row]:
        """Получает список студентов на текущей паре"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT s.user_id, s.full_name, s.group_name, cc.joined_at
                FROM students s
                JOIN current_class cc ON s.user_id = cc.user_id
                ORDER BY s.full_name
            ''')
            return cursor.fetchall()
    
    def clear_current_class(self) -> bool:
        """Очищает текущую пару"""
        try:
            with self.get_connection() as conn:
                conn.execute('DELETE FROM current_class')
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка очистки пары: {e}")
            return False
    
    def update_student_info(self, user_id: str, full_name: str = None, group_name: str = None) -> bool:
        """Обновляет информацию о студенте"""
        try:
            with self.get_connection() as conn:
                if full_name and group_name:
                    conn.execute(
                        'UPDATE students SET full_name = ?, group_name = ? WHERE user_id = ?',
                        (full_name, group_name, user_id)
                    )
                elif full_name:
                    conn.execute(
                        'UPDATE students SET full_name = ? WHERE user_id = ?',
                        (full_name, user_id)
                    )
                elif group_name:
                    conn.execute(
                        'UPDATE students SET group_name = ? WHERE user_id = ?',
                        (group_name, user_id)
                    )
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка обновления студента: {e}")
            return False