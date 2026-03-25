"""
Парсер файлов аннотаций.
Считывает EDU, слова и жесты (HandGest, HeadGest) из txt файлов и
добавляет данные в базу.
Другие слои игнорируются.
"""

import re
import os
import pymorphy3
from database import CorpusDatabase


class CorpusParser:

    def __init__(self, db: CorpusDatabase):
        self.db = db
        self.current_video_id = None
        self.morph = pymorphy3.MorphAnalyzer()

    def _lemmatize_word(self, word: str) -> str:
        """Лемматизирует слово с помощью pymorphy3."""
        try:
            parsed = self.morph.parse(word)[0]
            return parsed.normal_form
        except:
            return word

    def parse_file(self, filepath: str):
        base = os.path.basename(filepath).replace('.txt', '')
        video_filename = f"{base}.mp4"

        self.current_video_id = self.db.add_video(video_filename, f"videos/{video_filename}")

        # Читаем файл
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

        # Список для хранения соответствия времени и ID EDU
        edu_map = []  # список кортежей (start, end, id)

        # ==================== ПЕРВЫЙ ПРОХОД: EDU ====================
        for line in lines:
            line = line.strip()
            if not line:
                continue

            raw_parts = line.split('\t')

            if len(raw_parts) < 8:
                continue

            tier = raw_parts[0]
            if tier == 'EDU':
                try:
                    start_str = raw_parts[2]
                    end_str = raw_parts[4]
                    value = raw_parts[8]

                    start_time = self._parse_time(start_str)
                    end_time = self._parse_time(end_str)

                    clean_text = re.sub(r'\(\d+\.?\d*\)', '', value)
                    clean_text = clean_text.strip()

                    edu_id = self.db.add_edu(
                            video_id=self.current_video_id,
                            text=clean_text[:100] + '...' if len(clean_text) > 100 else clean_text,
                            start=start_time,
                            end=end_time,
                            full_text=clean_text
                        )
                    edu_map.append((start_time, end_time, edu_id))
                except Exception as e:
                    pass

        edu_map.sort(key=lambda x: x[0])

        # ==================== ВТОРОЙ ПРОХОД: СЛОВА И ЖЕСТЫ ====================
        for line in lines:
            line = line.strip()
            if not line:
                continue

            raw_parts = line.split('\t')

            tier = raw_parts[0]

            # Пропускаем EDU (уже обработаны)
            if tier == 'EDU':
                continue

            try:
                start_str = raw_parts[2]
                end_str = raw_parts[4]
                value = raw_parts[-1]

                start_time = self._parse_time(start_str)
                end_time = self._parse_time(end_str)

                # -------------------- СЛОВА --------------------
                if tier == 'Words':
                    if not value or value.startswith('(') or value.startswith('h(') or value.startswith('{'):
                        continue

                    clean_word = re.sub(r'[<>?]', '', value)
                    clean_word = re.sub(r'[^\w\s-]', '', clean_word)
                    clean_word = clean_word.strip()

                    if clean_word:
                        # Находим EDU, который содержит это слово
                        edu_id = None
                        for e_start, e_end, e_id in edu_map:
                            if e_start <= start_time <= e_end:
                                edu_id = e_id
                                break

                        if edu_id:
                            lemma = self._lemmatize_word(clean_word)

                            self.db.add_word(
                                video_id=self.current_video_id,
                                edu_id=edu_id,
                                word=clean_word,
                                start=start_time,
                                end=end_time,
                                lemma=lemma
                            )

                # -------------------- ЖЕСТЫ --------------------
                # Обрабатываем только HandGest и HeadGest
                elif tier in ['HandGest', 'HeadGest']:
                    if value:
                        self.db.add_gesture(
                            video_id=self.current_video_id,
                            tier=tier,
                            value=value,
                            start=start_time,
                            end=end_time
                        )
            except Exception:
                continue


    def _parse_time(self, time_str: str) -> float:
        """Преобразует строку времени в секунды."""
        time_str = time_str.strip()

        parts = time_str.split(':')
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds