"""
Модуль для работы с базой данных SQLite.
Хранит аннотации: видео, EDU, слова, жесты (HandGest, HeadGest).
"""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime


class CorpusDatabase:
    """
    Класс для управления базой данных корпуса жестов и речи.

    Таблицы:
    - videos: информация о видеофайлах
    - edu: речевые единицы (фразы)
    - words: слова с таймкодами и леммами
    - gestures: жесты с типом (HandGest, HeadGest)
    """

    def __init__(self, db_path: str = 'data/corpus.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Создает все таблицы и индексы, если они не существуют."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Таблица видео
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    filepath TEXT,
                    date_added TIMESTAMP
                )
            ''')

            # Таблица EDU (речевые единицы)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS edu (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER,
                    text TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration REAL,
                    full_text TEXT,
                    FOREIGN KEY (video_id) REFERENCES videos (id)
                )
            ''')

            # Таблица слов с таймкодами и леммами
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER,
                    edu_id INTEGER,
                    word TEXT,
                    lemma TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration REAL,
                    normalized_word TEXT,
                    FOREIGN KEY (video_id) REFERENCES videos (id),
                    FOREIGN KEY (edu_id) REFERENCES edu (id)
                )
            ''')

            # Таблица жестов (только HandGest и HeadGest)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gestures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER,
                    tier TEXT,
                    gesture_type TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration REAL,
                    FOREIGN KEY (video_id) REFERENCES videos (id)
                )
            ''')

            # Индексы для быстрого поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_word ON words(normalized_word)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_lemma ON words(lemma)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_video ON words(video_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gestures_type ON gestures(gesture_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gestures_tier ON gestures(tier)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gestures_video ON gestures(video_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_edu_video ON edu(video_id)')

            conn.commit()

    # ==================== ДОБАВЛЕНИЕ ДАННЫХ ====================

    def add_video(self, filename: str, filepath: str) -> Optional[int]:
        """Добавляет видео в базу данных."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO videos (filename, filepath, date_added)
                    VALUES (?, ?, ?)
                ''', (filename, filepath, datetime.now()))
                conn.commit()
            except:
                pass

            cursor.execute('SELECT id FROM videos WHERE filename = ?', (filename,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_video_id(self, filename: str) -> Optional[int]:
        """Получает ID видео по имени файла."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM videos WHERE filename = ?', (filename,))
            result = cursor.fetchone()
            return result[0] if result else None

    def add_edu(self, video_id: int, text: str, start: float, end: float, full_text: str = None) -> Optional[int]:
        """Добавляет EDU в базу данных."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO edu (video_id, text, start_time, end_time, duration, full_text)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (video_id, text, start, end, end - start, full_text or text))
            conn.commit()
            return cursor.lastrowid

    def add_word(self, video_id: int, edu_id: int, word: str, start: float, end: float, lemma: str = None):
        """Добавляет слово в базу данных."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO words (video_id, edu_id, word, lemma, start_time, end_time, duration, normalized_word)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (video_id, edu_id, word, lemma, start, end, end - start, word.lower()))
            conn.commit()

    def add_gesture(self, video_id: int, tier: str, value: str, start: float, end: float):
        """Добавляет жест в базу данных (только HandGest и HeadGest)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO gestures (video_id, tier, gesture_type, start_time, end_time, duration)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (video_id, tier, value, start, end, end - start))
            conn.commit()

    # ==================== ПОЛУЧЕНИЕ ДАННЫХ ====================

    def get_videos_list(self) -> List[Dict]:
        """Получает список всех видео в базе."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT id, filename, filepath, date_added FROM videos ORDER BY filename')
            return [dict(row) for row in cursor.fetchall()]

    # ==================== ПОИСК ====================

    def search_by_word(self, query: str, video_id: int = None) -> List[Dict]:
        """Поиск по словам."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            sql = '''
                SELECT
                    w.id,
                    w.video_id,
                    w.edu_id,
                    w.word,
                    w.lemma,
                    w.start_time as word_start,
                    w.end_time as word_end,
                    v.filename as video_filename,
                    e.text as edu_text,
                    e.start_time as edu_start,
                    e.end_time as edu_end
                FROM words w
                JOIN videos v ON w.video_id = v.id
                JOIN edu e ON w.edu_id = e.id
                WHERE w.normalized_word LIKE ?
            '''
            params = [f'%{query.lower()}%']

            if video_id:
                sql += ' AND w.video_id = ?'
                params.append(video_id)

            sql += ' ORDER BY v.filename, w.start_time LIMIT 200'

            cursor.execute(sql, params)
            results = []

            for row in cursor.fetchall():
                start_time = row['edu_start']
                end_time = row['edu_end']
                video_path = row['video_filename']

                results.append({
                    'type': 'word',
                    'video_id': row['video_id'],
                    'video': row['video_filename'],
                    'video_path': video_path,
                    'word': row['word'],
                    'lemma': row['lemma'],
                    'word_start': row['word_start'],
                    'word_end': row['word_end'],
                    'edu_text': row['edu_text'],
                    'start_time': start_time,
                    'end_time': end_time
                })

        return results

    def search_by_lemma(self, query: str, video_id: int = None) -> List[Dict]:
        """Поиск по леммам слов."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            sql = '''
                SELECT
                    w.id,
                    w.video_id,
                    w.edu_id,
                    w.word,
                    w.lemma,
                    w.start_time as word_start,
                    w.end_time as word_end,
                    v.filename as video_filename,
                    e.text as edu_text,
                    e.start_time as edu_start,
                    e.end_time as edu_end
                FROM words w
                JOIN videos v ON w.video_id = v.id
                LEFT JOIN edu e ON w.edu_id = e.id
                WHERE w.lemma LIKE ?
            '''
            params = [f'%{query.lower()}%']

            if video_id:
                sql += ' AND w.video_id = ?'
                params.append(video_id)

            sql += ' ORDER BY v.filename, w.start_time LIMIT 200'

            cursor.execute(sql, params)
            results = []
            seen = set()

            for row in cursor.fetchall():
                start_time = row['edu_start'] if row['edu_start'] else row['word_start']
                end_time = row['edu_end'] if row['edu_end'] else row['word_end']
                video_path = row['video_filename']

                results.append({
                    'type': 'lemma',
                    'video_id': row['video_id'],
                    'video': row['video_filename'],
                    'video_path': video_path,
                    'word': row['word'],
                    'lemma': row['lemma'],
                    'word_start': row['word_start'],
                    'word_end': row['word_end'],
                    'edu_text': row['edu_text'],
                    'start_time': start_time,
                    'end_time': end_time
                })

        return results

    def search_by_gesture(self, gesture_type: str = None, video_id: int = None) -> List[Dict]:
        """Поиск по жестам (только по типу жеста)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            sql = '''
                SELECT
                    g.id,
                    g.video_id,
                    g.tier,
                    g.gesture_type,
                    g.start_time as gesture_start,
                    g.end_time as gesture_end,
                    v.filename as video_filename,
                    e.text as edu_text,
                    e.start_time as edu_start,
                    e.end_time as edu_end
                FROM gestures g
                JOIN videos v ON g.video_id = v.id
                LEFT JOIN edu e ON e.video_id = g.video_id 
                    AND e.start_time <= g.end_time 
                    AND e.end_time >= g.start_time
                WHERE 1=1
            '''
            params = []

            if gesture_type:
                sql += ' AND g.gesture_type = ?'
                params.append(gesture_type)

            if video_id:
                sql += ' AND g.video_id = ?'
                params.append(video_id)

            sql += ' ORDER BY v.filename, g.start_time LIMIT 200'

            cursor.execute(sql, params)
            results = []
            seen = set()

            for row in cursor.fetchall():
                key = f"{row['video_id']}_{row['tier']}_{row['gesture_start']:.3f}"
                if key not in seen:
                    seen.add(key)

                    start_time = row['gesture_start']
                    end_time = row['gesture_end']
                    edu_text = row['edu_text'] if row['edu_text'] else ''
                    video_path = row['video_filename']

                    results.append({
                        'type': 'gesture',
                        'video_id': row['video_id'],
                        'video': row['video_filename'],
                        'video_path': video_path,
                        'tier': row['tier'],
                        'gesture_type': row['gesture_type'],
                        'gesture_start': row['gesture_start'],
                        'gesture_end': row['gesture_end'],
                        'edu_text': edu_text,
                        'start_time': start_time,
                        'end_time': end_time
                    })

            return results

    # ==================== АННОТАЦИИ ДЛЯ СЕГМЕНТА ====================

    def get_annotations_in_range(self, video_id: int, start: float, end: float) -> Dict[str, List]:
        """
        Получает все аннотации для заданного временного отрезка.
        Слои: EDU, Words, Lemmas, HandGest, HeadGest
        """
        result = {}

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # EDU
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM edu 
                WHERE video_id = ? AND start_time <= ? AND end_time >= ?
                ORDER BY start_time
            ''', (video_id, end, start))
            result['EDU'] = [dict(row) for row in cursor.fetchall()]

            # Lemmas (уникальные леммы в диапазоне)
            cursor.execute('''
                SELECT lemma as value, lemma, start_time, end_time 
                FROM words 
                WHERE video_id = ? AND start_time <= ? AND end_time >= ? AND lemma IS NOT NULL
                ORDER BY start_time
            ''', (video_id, end, start))

            lemmas = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                row_dict['value'] = row_dict['lemma']
                lemmas.append(row_dict)
            result['Lemmas'] = lemmas

            # Words
            cursor.execute('''
                SELECT word, start_time, end_time 
                FROM words 
                WHERE video_id = ? AND start_time <= ? AND end_time >= ?
                ORDER BY start_time
            ''', (video_id, end, start))
            result['Words'] = [dict(row) for row in cursor.fetchall()]

            # Жесты (HandGest и HeadGest)
            cursor.execute('''
                SELECT * FROM gestures 
                WHERE video_id = ? AND start_time <= ? AND end_time >= ?
                ORDER BY start_time
            ''', (video_id, end, start))

            for g in cursor.fetchall():
                g_dict = dict(g)
                tier = g_dict['tier']
                if tier not in result:
                    result[tier] = []
                result[tier].append(g_dict)

        return result