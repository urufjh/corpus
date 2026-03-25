class CorpusPlayer {
    constructor() {
        // DOM элементы
        this.video = document.getElementById('video-player');
        this.videoPlaceholder = document.getElementById('video-placeholder');
        this.videoTitle = document.getElementById('video-title');
        this.annotationsSection = document.getElementById('annotations-section');
        this.searchInput = document.getElementById('search-input');
        this.searchBtn = document.getElementById('search-btn');
        this.searchGestureBtn = document.getElementById('search-gesture-btn');
        this.resultsDiv = document.getElementById('search-results');
        this.resultsCount = document.getElementById('results-count');
        this.annotationsDiv = document.getElementById('annotations');
        this.videoSelect = document.getElementById('video-select');
        this.gestureTypeSelect = document.getElementById('gesture-type-select');
        this.wordSearchBox = document.getElementById('word-search-box');
        this.gestureSearchBox = document.getElementById('gesture-search-box');

        // Состояние
        this.currentResults = [];
        this.currentVideo = null;
        this.currentSegment = null;
        this.currentVideoId = null;
        this.currentTime = 0;

        this.initEventListeners();
    }

    initEventListeners() {
        // Переключение вкладок поиска
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');

                const type = e.target.dataset.type;
                if (type === 'gesture') {
                    this.wordSearchBox.style.display = 'none';
                    this.gestureSearchBox.style.display = 'flex';
                    this.searchInput.value = '';
                } else {
                    this.wordSearchBox.style.display = 'flex';
                    this.gestureSearchBox.style.display = 'none';
                }

                this.resultsDiv.innerHTML = '';
                this.resultsCount.textContent = '(0)';
            });
        });

        // Поиск по словам и леммам
        this.searchBtn.addEventListener('click', () => this.searchWordLemma());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchWordLemma();
        });

        // Поиск по жестам
        if (this.searchGestureBtn) {
            this.searchGestureBtn.addEventListener('click', () => this.searchGesture());
        }

        // Обновление playhead
        this.video.addEventListener('timeupdate', () => {
            this.currentTime = this.video.currentTime;
            this.updatePlayhead();
        });

        this.video.addEventListener('loadedmetadata', () => {
            console.log('Video loaded, duration:', this.video.duration);
        });

        this.video.addEventListener('error', (e) => {
            console.error('Video error:', e);
        });
    }

    async searchWordLemma() {
        const query = this.searchInput.value.trim();
        if (!query) {
            alert('Введите поисковый запрос');
            return;
        }

        const activeTab = document.querySelector('.tab-btn.active');
        const searchType = activeTab.dataset.type;
        const videoId = this.videoSelect.value;

        let url = `/api/search?q=${encodeURIComponent(query)}&type=${searchType}`;

        if (videoId) {
            url += `&video_id=${videoId}`;
        }

        try {
            console.log('Searching:', url);
            const response = await fetch(url);
            const results = await response.json();
            this.currentResults = results;
            this.displayResults(results);
        } catch (error) {
            console.error('Search error:', error);
            alert('Ошибка при поиске');
        }
    }

    async searchGesture() {
        const gestureType = this.gestureTypeSelect ? this.gestureTypeSelect.value : '';
        const videoId = this.videoSelect.value;

        if (!gestureType) {
            alert('Выберите тип жеста');
            return;
        }

        let url = `/api/search?type=gesture&gesture_type=${encodeURIComponent(gestureType)}`;

        if (videoId) {
            url += `&video_id=${videoId}`;
        }

        console.log('Searching gestures:', url);

        try {
            const response = await fetch(url);
            const results = await response.json();

            if (results.error) {
                alert(results.error);
                return;
            }

            this.currentResults = results;
            this.displayResults(results);
        } catch (error) {
            console.error('Search error:', error);
            alert('Ошибка при поиске жестов');
        }
    }

    displayResults(results) {
        if (results.length === 0) {
            this.resultsDiv.innerHTML = '<p class="no-results">Ничего не найдено</p>';
            this.resultsCount.textContent = '(0)';
            return;
        }

        this.resultsCount.textContent = `(${results.length})`;

        const grouped = {};
        results.forEach(result => {
            if (!grouped[result.video]) {
                grouped[result.video] = [];
            }
            grouped[result.video].push(result);
        });

        let html = '';
        for (const [video, videoResults] of Object.entries(grouped)) {
            html += `<div class="video-group">`;
            html += `<h3 class="video-group-title">📹 ${video}</h3>`;

            videoResults.forEach((result) => {
                const startTime = result.start_time || result.edu_start || result.word_start || result.gesture_start || 0;
                const endTime = result.end_time || result.edu_end || result.word_end || result.gesture_end || 0;
                const fileName = result.video_path;

                let displayWord = '';
                let resultType = result.type;
                let badgeIcon = '🔤';

                if (result.type === 'word') {
                    displayWord = result.word;
                    badgeIcon = '🔤';
                } else if (result.type === 'lemma') {
                    displayWord = result.lemma;
                    resultType = 'lemma';
                    badgeIcon = '📖';
                } else if (result.type === 'gesture') {
                    displayWord = `${result.gesture_type} (${result.tier})`;
                    badgeIcon = '👐';
                }

                html += `
                    <div class="result-item" data-video="${result.video}"
                         data-video-id="${result.video_id}"
                         data-video-path="${fileName}"
                         data-start="${startTime}"
                         data-end="${endTime}"
                         onclick="player.loadSegment('${fileName}', ${result.video_id}, ${startTime}, ${endTime})">
                        <div class="result-badge ${resultType}">${badgeIcon}</div>
                        <div class="result-content">
                            <div class="result-main">
                                <span class="result-${resultType}">${displayWord}</span>
                            </div>
                            <div class="result-context">${result.edu_text || 'Нет текста'}</div>
                            <div class="result-time">
                                ${this.formatTime(startTime)} - ${this.formatTime(endTime)}
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `</div>`;
        }

        this.resultsDiv.innerHTML = html;
    }

    async loadSegment(videoPath, videoId, start, end) {
        console.log('Loading segment:', {videoPath, videoId, start, end});

        this.currentVideoId = videoId;

        if (window.gestureChart) {
            window.gestureChart.setVideoId(videoId);
        }

        if (this.videoTitle) {
            this.videoTitle.textContent = `▶ ${videoPath}`;
        }

        this.video.style.display = 'block';
        this.videoPlaceholder.style.display = 'none';
        this.annotationsSection.style.display = 'block';

        const videoSource = this.video.querySelector('source');
        const currentVideo = videoSource.getAttribute('src');
        const newVideoPath = `/video/${videoPath}`;

        if (currentVideo !== newVideoPath) {
            videoSource.setAttribute('src', newVideoPath);
            this.video.load();

            this.video.onloadeddata = () => {
                this.video.currentTime = start;
                this.video.play().catch(e => console.error('Play error:', e));
            };
        } else {
            this.video.currentTime = start;
            this.video.play().catch(e => console.error('Play error:', e));
        }

        this.currentSegment = { start, end, videoPath, videoId };

        document.querySelectorAll('.result-item').forEach(item => {
            item.classList.remove('active');
        });
        if (event && event.currentTarget) {
            event.currentTarget.classList.add('active');
        }

        await this.loadAnnotations(videoId, start, end);
    }

    async loadAnnotations(videoId, start, end) {
        try {
            const bufferStart = Math.max(0, start - 2);
            const bufferEnd = end + 2;

            const url = `/api/segment/${videoId}/${bufferStart}/${bufferEnd}`;
            const response = await fetch(url);
            const annotations = await response.json();

            this.displayAnnotations(annotations);
        } catch (error) {
            console.error('Error loading annotations:', error);
        }
    }

    displayAnnotations(annotations) {
        const tierOrder = ['EDU', 'Words', 'Lemmas', 'HandGest', 'HeadGest'];

        let html = '';
        let hasAnnotations = false;

        if (!this.currentSegment) return;

        const segmentStart = this.currentSegment.start;
        const segmentEnd = this.currentSegment.end;
        const segmentDuration = segmentEnd - segmentStart;

        html += '<div class="timeline-horizontal">';
        html += '<div class="timeline-ruler">';
        for (let time = Math.floor(segmentStart); time <= Math.ceil(segmentEnd); time += 5) {
            const position = ((time - segmentStart) / segmentDuration) * 100;
            if (position >= 0 && position <= 100) {
                html += `<div class="ruler-marker" style="left: ${position}%">${this.formatTime(time)}</div>`;
            }
        }
        html += '</div>';

        html += `<div class="playhead-overlay"><div class="playhead" id="playhead"></div></div>`;

        tierOrder.forEach(tier => {
            if (annotations[tier] && annotations[tier].length > 0) {
                hasAnnotations = true;

                html += `<div class="tier-row">`;
                html += `<div class="tier-label ${tier.toLowerCase()}">${tier}</div>`;
                html += `<div class="tier-track">`;

                annotations[tier].forEach(ann => {
                    let startTime = ann.start_time || ann.start || 0;
                    let endTime = ann.end_time || ann.end || 0;

                    if (endTime < segmentStart || startTime > segmentEnd) return;

                    startTime = Math.max(startTime, segmentStart);
                    endTime = Math.min(endTime, segmentEnd);

                    const left = ((startTime - segmentStart) / segmentDuration) * 100;
                    const width = ((endTime - startTime) / segmentDuration) * 100;

                    let value = '';
                    if (tier === 'EDU') {
                        value = ann.text || ann.full_text || '';
                    } else if (tier === 'Lemmas') {
                        value = ann.value || ann.lemma || '';
                    } else if (tier === 'Words') {
                        value = ann.word || '';
                    } else {
                        value = ann.gesture_type || '';
                    }

                    const tierClass = tier.toLowerCase();

                    let displayValue = value;
                    if (tier !== 'EDU' && value.length > 35) {
                        displayValue = value.substring(0, 32) + '...';
                    }

                    html += `
                        <div class="annotation-segment ${tierClass}"
                             style="left: ${left}%; width: ${width}%;"
                             data-start="${startTime}"
                             data-end="${endTime}"
                             onclick="event.stopPropagation(); player.seekToTime(${startTime})"
                             title="${this.formatTime(startTime)} - ${this.formatTime(endTime)}\n${value}">
                            <span class="segment-label">${displayValue}</span>
                        </div>
                    `;
                });

                html += `</div></div>`;
            }
        });

        html += '</div>';

        if (!hasAnnotations) {
            html = '<p class="no-annotations">Нет аннотаций для этого фрагмента</p>';
        }

        this.annotationsDiv.innerHTML = html;

        document.querySelectorAll('.tier-track').forEach(track => {
            track.addEventListener('click', (e) => {
                if (e.target.closest('.annotation-segment')) return;

                const rect = track.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const percentage = clickX / rect.width;
                const seekTime = this.currentSegment.start + (percentage * (this.currentSegment.end - this.currentSegment.start));
                this.seekToTime(seekTime);
            });
        });

        this.updatePlayhead();
    }

    seekToTime(time) {
        if (this.video) {
            this.video.currentTime = time;
            this.video.play();
        }
    }

    updatePlayhead() {
        if (!this.currentSegment) return;

        const playhead = document.getElementById('playhead');
        if (!playhead) return;

        const currentTime = this.video.currentTime;
        const { start, end } = this.currentSegment;

        if (currentTime >= start && currentTime <= end) {
            const duration = end - start;
            const percentage = ((currentTime - start) / duration) * 100;
            playhead.style.left = `${percentage}%`;
            playhead.style.display = 'block';
        } else {
            playhead.style.display = 'none';
        }
    }

    formatTime(seconds) {
        if (isNaN(seconds)) return '00:00.000';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
    }
}

// ============================================
// КЛАСС: ГРАФИК СТАТИСТИКИ ЖЕСТОВ
// ============================================

class GestureChart {
    constructor() {
        this.container = document.getElementById('gesture-chart-container');
        this.chartImg = document.getElementById('gesture-chart-img');
        this.chartData = document.getElementById('gesture-chart-data');
        this.buttonContainer = document.getElementById('chart-button-container');
        this.currentVideoId = null;
        this.init();
    }

    init() {
        const showBtn = document.getElementById('show-gesture-chart');
        const closeBtn = document.getElementById('close-chart');

        if (showBtn) {
            showBtn.addEventListener('click', () => this.show());
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }
    }

    setVideoId(videoId) {
        this.currentVideoId = videoId;
        if (this.buttonContainer) {
            this.buttonContainer.style.display = 'block';
        }
    }

    async show() {
        if (!this.currentVideoId) {
            alert('Сначала выберите видео');
            return;
        }

        try {
            const response = await fetch(`/api/gesture_chart/${this.currentVideoId}`);
            const data = await response.json();

            if (data.error) {
                alert(data.error);
                return;
            }

            this.chartImg.src = `data:image/png;base64,${data.image}`;

            // Таблица с детальной статистикой по типам жестов
            let tableHtml = `
                <h4>Статистика по типам жестов:</h4>
                <table>
                    <thead>
                        <tr>
                            <th>Тип жеста</th>
                            <th>Количество</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            data.detail_data.forEach(item => {
                tableHtml += `
                    <tr>
                        <td>${item.type}</td>
                        <td>${item.count}</td>
                    </tr>
                `;
            });

            // Добавляем итоговую строку
            const total = data.detail_data.reduce((sum, item) => sum + item.count, 0);
            tableHtml += `
                    </tbody>
                    <tfoot>
                        <tr style="background-color: #f0f0f0; font-weight: bold;">
                            <td>Всего:</td>
                            <td>${total}</td>
                        </tr>
                    </tfoot>
                </table>
            `;

            // Также можно добавить сводку по рукам и голове
            let summaryHtml = `
                <h4>Сводка по категориям:</h4>
                <table>
                    <thead>
                        <tr>
                            <th>Категория</th>
                            <th>Количество</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            data.chart_data.forEach(item => {
                summaryHtml += `
                    <tr>
                        <td>${item.tier}</td>
                        <td>${item.count}</td>
                    </tr>
                `;
            });
            summaryHtml += `</tbody></table>`;

            // Показываем обе таблицы
            this.chartData.innerHTML = summaryHtml + '<br>' + tableHtml;

            this.container.style.display = 'block';
            this.container.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            console.error('Error loading chart:', error);
            alert('Ошибка загрузки графика');
        }
    }

    hide() {
        this.container.style.display = 'none';
    }
}

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    window.player = new CorpusPlayer();
    window.gestureChart = new GestureChart();
});