// history.js

document.addEventListener('DOMContentLoaded', function() {
  // Проверка авторизации
  const token = getToken();
  if (!token) {
    window.location.href = '/login/';
    return;
  }

  const role = getRole();
  document.getElementById('userRole').textContent = role === 'ADMIN' ? 'Администратор' : 'Пользователь';

  // Кнопки
  document.getElementById('logoutBtn').addEventListener('click', logout);
  document.getElementById('backToMainBtn').addEventListener('click', function() {
    window.location.href = '/main/';
  });

  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  const historyList = document.getElementById('historyList');
  const resultModal = document.getElementById('resultModal');
  const modalBody = document.getElementById('modalBody');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const closeModalFooterBtn = document.getElementById('closeModalFooterBtn');
  const copyResultBtn = document.getElementById('copyResultBtn');

  let currentResultText = '';

  // Закрытие модалки
  function closeModal() {
    resultModal.classList.add('hidden');
  }

  closeModalBtn.addEventListener('click', closeModal);
  closeModalFooterBtn.addEventListener('click', closeModal);
  resultModal.addEventListener('click', function(e) {
    if (e.target === resultModal) closeModal();
  });

  // Копирование текста
  copyResultBtn.addEventListener('click', function() {
    if (currentResultText) {
      navigator.clipboard.writeText(currentResultText);
      showToast('Текст скопирован', 'success');
    }
  });

  // Загрузка истории (МОК)
  function loadHistory() {
    // TODO: заменить на реальный API
    // GET /api/history
    
    const mockHistory = [
      {
        id: 1,
        date: '2026-06-06 14:30:00',
        actionType: 'summary',
        description: 'Саммари по кластерам',
        details: 'Кластеров: 10, Каналов: 5, Период: 30.05.2026 - 06.06.2026',
        result: {
          clusters: [
            { topic: 'Международные переговоры', count: 38, summary: '15 марта в Женеве прошёл очередной раунд переговоров...', sources: ['ТАСС', 'РБК'] },
            { topic: 'Новые технологии', count: 24, summary: 'Российские компании внедряют ИИ...', sources: ['Коммерсантъ'] }
          ]
        }
      },
      {
        id: 2,
        date: '2026-06-05 10:15:00',
        actionType: 'search',
        description: 'Поиск: Иванов',
        details: 'Найдено 3 кластера',
        result: { query: 'Иванов', results: ['Кластер 1', 'Кластер 2'] }
      },
      {
        id: 3,
        date: '2026-06-04 09:00:00',
        actionType: 'graph',
        description: 'График кластеров',
        details: 'Кластеров: 10',
        result: { imageUrl: 'mock.png' }
      },
      {
        id: 4,
        date: '2026-06-03 18:20:00',
        actionType: 'tts',
        description: 'Прослушать подкаст',
        details: 'Озвучка саммари',
        result: { audioUrl: 'mock.mp3' }
      },
      {
        id: 5,
        date: '2026-06-02 12:00:00',
        actionType: 'timeline',
        description: 'Хронология: Международные переговоры',
        details: 'Построена хронология по теме',
        result: { events: ['Событие 1', 'Событие 2', 'Событие 3'] }
      }
    ];

    renderHistory(mockHistory);
  }

  function renderHistory(entries) {
    if (!entries || entries.length === 0) {
      historyList.innerHTML = `
        <div class="empty-state">
          <p>📭 История пуста</p>
          <p style="font-size: 13px; margin-top: 8px;">Выполните действия на главной странице</p>
        </div>
      `;
      return;
    }

    let html = '';
    entries.forEach(function(entry) {
      let actionIcon = '📋';
      if (entry.actionType === 'summary') actionIcon = '📊';
      if (entry.actionType === 'search') actionIcon = '🔍';
      if (entry.actionType === 'graph') actionIcon = '📈';
      if (entry.actionType === 'tts') actionIcon = '🎧';
      if (entry.actionType === 'timeline') actionIcon = '📅';
      
      html += `
        <div class="history-item" data-id="${entry.id}" data-type="${entry.actionType}" data-result='${JSON.stringify(entry.result)}'>
          <div class="history-item-header">
            <span class="history-date">${actionIcon} ${entry.date}</span>
            <span class="history-badge">${entry.description}</span>
          </div>
          <div class="history-description">${entry.details}</div>
        </div>
      `;
    });
    
    historyList.innerHTML = html;
    
    // Добавляем обработчики на историю
    document.querySelectorAll('.history-item').forEach(function(item) {
      item.addEventListener('click', function() {
        const actionType = this.dataset.type;
        let result;
        try {
          result = JSON.parse(this.dataset.result);
        } catch(e) {
          result = {};
        }
        showResultModal(actionType, result);
      });
    });
  }

  function showResultModal(actionType, result) {
    let html = '';
    currentResultText = '';
    
    switch(actionType) {
      case 'summary':
        if (result.clusters) {
          result.clusters.forEach(function(cluster, idx) {
            html += `
              <div class="result-cluster">
                <div class="result-cluster-title">Кластер ${idx+1}: ${cluster.topic} (${cluster.count} новостей)</div>
                <div class="result-cluster-summary">${cluster.summary}</div>
                <div class="result-cluster-sources">📡 Источники: ${cluster.sources.join(', ')}</div>
              </div>
            `;
          });
          currentResultText = result.clusters.map(c => `${c.topic}\n${c.summary}`).join('\n\n');
        } else {
          html = '<div>Нет данных для отображения</div>';
        }
        break;
        
      case 'search':
        html = `<div><strong>Поисковый запрос:</strong> ${result.query || 'не указан'}</div>
                <div style="margin-top: 12px;"><strong>Результаты:</strong> ${(result.results || []).join(', ') || 'ничего не найдено'}</div>`;
        currentResultText = `Запрос: ${result.query}\nРезультаты: ${(result.results || []).join(', ')}`;
        break;
        
      case 'graph':
        html = `<div class="stats-graph-placeholder" style="text-align: center; padding: 40px;">
                  📈 <strong>График кластеров</strong><br>
                  <div style="margin-top: 16px; padding: 20px; background: var(--bg-primary); border-radius: 8px;">
                    [Здесь будет изображение графика]
                  </div>
                </div>`;
        currentResultText = 'График кластеров (изображение)';
        break;
        
      case 'tts':
        html = `<div class="stats-graph-placeholder" style="text-align: center; padding: 40px;">
                  🎧 <strong>Аудио озвучка</strong><br>
                  <div style="margin-top: 16px;">
                    <audio controls src="${result.audioUrl || ''}">
                      Ваш браузер не поддерживает аудио
                    </audio>
                  </div>
                </div>`;
        currentResultText = 'Аудиофайл с озвучкой саммари';
        break;
        
      case 'timeline':
        if (result.events) {
          html = '<div><strong>Хронология событий:</strong></div><ul style="margin-top: 12px; list-style: none; padding-left: 0;">';
          result.events.forEach(function(event, idx) {
            html += `<li style="margin-bottom: 12px; padding-left: 20px; border-left: 2px solid var(--accent);">🔹 ${event}</li>`;
          });
          html += '</ul>';
          currentResultText = result.events.join('\n');
        } else {
          html = '<div>Нет событий для отображения</div>';
        }
        break;
        
      default:
        html = '<div>Неизвестный тип действия</div>';
    }
    
    modalBody.innerHTML = html;
    resultModal.classList.remove('hidden');
  }

  // Очистка истории
  clearHistoryBtn.addEventListener('click', function() {
    if (confirm('Вы уверены, что хотите очистить всю историю? Действие необратимо.')) {
      // TODO: реальный API DELETE /api/history
      showToast('История очищена (демо-режим)', 'success');
      loadHistory(); // Перезагружаем пустую историю
    }
  });

  // Загружаем историю при старте
  loadHistory();
});