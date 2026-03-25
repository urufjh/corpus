from flask import Flask, render_template, request, jsonify, send_from_directory
from database import CorpusDatabase
from data_parser import CorpusParser
import os
import sqlite3

import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# Конфигурация
DATA_FOLDER = 'data'
VIDEO_FOLDER = 'data\\videos'
ANNOTATIONS_FOLDER = 'data\\annotations'
DB_PATH = 'data\\corpus.db'

# Инициализация базы данных
db = CorpusDatabase(DB_PATH)


def load_new_annotations():
    """Парсит файлы, для которых еще нет видео в базе."""
    parser = CorpusParser(db)

    existing_videos = {v['filename'].replace('.mp4', '') for v in db.get_videos_list()}
    txt_files = [f for f in os.listdir(ANNOTATIONS_FOLDER) if f.endswith('.txt')]

    new_files = []
    for f in txt_files:
        base_name = f.replace('.txt', '')
        if base_name not in existing_videos:
            new_files.append(f)

    if not new_files:
        return

    for filename in new_files:
        filepath = 'data\\annotations\\' + filename
        parser.parse_file(filepath)


@app.route('/')
def index():
    videos = db.get_videos_list()
    return render_template('index.html', videos=videos)


@app.route('/api/search')
def search():
    query = request.args.get('q', '').lower()
    search_type = request.args.get('type')
    video_id = request.args.get('video_id', type=int)
    gesture_type = request.args.get('gesture_type', '')

    if search_type == 'word':
        results = db.search_by_word(query, video_id)
    elif search_type == 'lemma':
        results = db.search_by_lemma(query, video_id)
    elif search_type == 'gesture':
        results = db.search_by_gesture(gesture_type, video_id)
    else:
        results = []
    return jsonify(results)


@app.route('/api/segment/<int:video_id>/<float:start>/<float:end>')
def get_segment_annotations(video_id, start, end):
    annotations = db.get_annotations_in_range(video_id, start, end)
    return jsonify(annotations)


@app.route('/video/<path:filename>')
def video_file(filename):
    return send_from_directory(VIDEO_FOLDER, filename)


@app.route('/api/gesture_chart/<int:video_id>')
def gesture_chart(video_id):
    """Генерирует график и возвращает детальную статистику жестов."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT filename FROM videos WHERE id = ?", (video_id,))
        result = cursor.fetchone()
        video_name = result[0]

        # Считаем общее количество жестов рук и головы для графика
        cursor.execute("""
            SELECT tier, COUNT(*) as count
            FROM gestures
            WHERE video_id = ?
            GROUP BY tier
            ORDER BY count DESC
        """, (video_id,))

        summary_data = cursor.fetchall()

        # Подготавливаем данные для графика (общие категории)
        chart_data = {}
        for tier, count in summary_data:
            if tier == 'HandGest':
                chart_data['Жесты рук'] = count
            elif tier == 'HeadGest':
                chart_data['Жесты головы'] = count

        # Детальная статистика по типам жестов (для таблицы)
        cursor.execute("""
            SELECT gesture_type, COUNT(*) as count
            FROM gestures
            WHERE video_id = ?
            GROUP BY gesture_type
            ORDER BY count DESC
        """, (video_id,))

        detail_data = cursor.fetchall()

        # Генерируем график
        fig, ax = plt.subplots(figsize=(8, 6))

        tiers = list(chart_data.keys())
        counts = list(chart_data.values())
        colors = ['#6D94C5', '#E8DFCA']

        bars = ax.bar(tiers, counts, color=colors, edgecolor='#9E001C', linewidth=1.5)

        ax.set_ylabel('Количество жестов', fontsize=12)
        ax.set_title(video_name.replace('.mp4', ''), fontsize=14, fontweight='bold')
        ax.set_facecolor('#F5EFE6')
        fig.patch.set_facecolor('#F5EFE6')
        ax.grid(axis='y', alpha=0.3)

        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    str(count), ha='center', va='bottom', fontsize=12, fontweight='bold')

        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()

        return jsonify({
            'video_name': video_name,
            'image': img_base64,
            'chart_data': [{'tier': k, 'count': v} for k, v in chart_data.items()],
            'detail_data': [{'type': row[0], 'count': row[1]} for row in detail_data]
        })


if __name__ == '__main__':
    load_new_annotations()
    app.run(debug=True, host='0.0.0.0', port=5000)