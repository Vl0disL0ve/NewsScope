// history.js — загружает историю действий пользователя (кластеры, поиск, TTS, графики, хронологии)

document.addEventListener('DOMContentLoaded', function () {
  const token = getToken();
  if (!token) {
    window.location.href = '/login/';
    return;
  }

  const role = getRole();
  document.getElementById('userRole').textContent = role === 'ADMIN' ? 'Администратор' : 'Пользователь';

  document.getElementById('logoutBtn').addEventListener('click', logout);
  document.getElementById('backToMainBtn').addEventListener('click', function () {
    window.location.href = '/main/';
  });

  const historyList = document.getElementById('historyList');
  const resultModal = document.getElementById('resultModal');
  const modalBody = document.getElementById('modalBody');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const closeModalFooterBtn = document.getElementById('closeModalFooterBtn');
  const copyResultBtn = document.getElementById('copyResultBtn');

  let currentResultText = '';

  function closeModal() {
    resultModal.classList.add('hidden');
  }
  closeModalBtn.addEventListener('click', closeModal);
  closeModalFooterBtn.addEventListener('click', closeModal);
  resultModal.addEventListener('click', function (e) {
    if (e.target === resultModal) closeModal();
  });
  copyResultBtn.addEventListener('click', function () {
    if (currentResultText) {
      navigator.clipboard.writeText(currentResultText);
      showToast('Текст скопирован', 'success');
    }
  });

  function esc(str) {
    if (!str) return '';
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  // ─── Загрузка истории ───────────────────────────────────────
  async function loadHistory() {
    historyList.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Загрузка...</p></div>';

    try {
      // Загружаем кластеры пользователя
      var resp = await fetch('/api/clusters/?limit=100', {
        headers: { 'Authorization': 'Bearer ' + getToken() }
      });
      if (!resp.ok) throw new Error('Ошибка загрузки');

      var data = await resp.json();
      var clusters = data.clusters || [];

      if (clusters.length === 0) {
        historyList.innerHTML =
          '<div class="empty-state">' +
          '<p>📭 История пуста</p>' +
          '<p style="font-size: 13px; margin-top: 8px;">Выполните действия на главной странице</p>' +
          '</div>';
        return;
      }

      // Строим список записей (entry): кластер + все действия с ним
      var entries = [];

      clusters.forEach(function (c) {
        var baseDate = (c.created_at || '').replace('T', ' ').slice(0, 19);

        // Основная запись — создание саммари
        entries.push({
          id: c.cluster_id,
          date: baseDate,
          actionType: 'summary',
          actionLabel: '📊 Саммари по кластерам',
          description: 'Тема: ' + (c.cluster_title || c.topic || '').slice(0, 60),
          details: 'Источники: ' + (c.news_sources || []).join(', ') +
            ' | Новостей: ' + (c.news_count || '?') +
            ' | ' + (c.date_from || '') + ' — ' + (c.date_to || ''),
          result: {
            cluster_id: c.cluster_id,
            topic: c.cluster_title || c.topic,
            summary: c.summary,
            sources: c.news_sources,
            available_actions: c.available_actions || []
          }
        });

        // Если есть аудио (TTS)
        if (c.audio_path) {
          entries.push({
            id: 'audio_' + c.cluster_id,
            date: baseDate,
            actionType: 'tts',
            actionLabel: '🎧 TTS по новости',
            description: 'Озвучка: ' + (c.cluster_title || c.topic || '').slice(0, 50),
            details: 'Аудиопересказ кластера #' + c.cluster_id,
            result: {
              cluster_id: c.cluster_id,
              topic: c.cluster_title || c.topic,
              audio_url: '/api/audio/' + c.cluster_id
            }
          });
        }

        // Если есть хронология
        if (c.chronology_path) {
          entries.push({
            id: 'chronology_' + c.cluster_id,
            date: baseDate,
            actionType: 'chronology',
            actionLabel: '📅 Хронология',
            description: 'Хронология: ' + (c.cluster_title || c.topic || '').slice(0, 50),
            details: 'Файл: ' + (c.chronology_path || ''),
            result: {
              cluster_id: c.cluster_id,
              topic: c.cluster_title || c.topic,
              chronology_path: c.chronology_path
            }
          });
        }

        // Действия из available_actions (поиск, график)
        var actions = c.available_actions || [];
        actions.forEach(function (action) {
          if (action === 'search') {
            entries.push({
              id: 'search_' + c.cluster_id,
              date: baseDate,
              actionType: 'search',
              actionLabel: '🔍 Поиск',
              description: 'Поиск по новостям',
              details: 'Связан с кластером #' + c.cluster_id,
              result: {
                cluster_id: c.cluster_id,
                topic: c.cluster_title || c.topic,
                summary: c.summary
              }
            });
          }
          if (action === 'plot') {
            entries.push({
              id: 'plot_' + c.cluster_id,
              date: baseDate,
              actionType: 'plot',
              actionLabel: '📈 График кластеров',
              description: 'График: ' + (c.cluster_title || c.topic || '').slice(0, 50),
              details: 'Визуализация распределения',
              result: {
                cluster_id: c.cluster_id,
                topic: c.cluster_title || c.topic
              }
            });
          }
        });
      });

      // Сортируем по дате (сначала новые)
      entries.sort(function (a, b) {
        return (b.date || '').localeCompare(a.date || '');
      });

      renderHistory(entries);
    } catch (err) {
      historyList.innerHTML =
        '<div class="empty-state">' +
        '<p>⚠️ Ошибка загрузки истории</p>' +
        '<p style="font-size:13px;color:var(--error)">' + esc(err.message) + '</p>' +
        '</div>';
    }
  }

  function renderHistory(entries) {
    var html = '';
    entries.forEach(function (entry) {
      var resultJson = JSON.stringify(entry.result).replace(/'/g, '&#39;').replace(/"/g, '&quot;');

      html +=
        '<div class="history-item" data-id="' + entry.id + '" data-type="' + entry.actionType + '" data-result=\'' + resultJson + '\'>' +
        '<div class="history-item-header">' +
        '<span class="history-date">' + esc(entry.date) + '</span>' +
        '<span class="history-badge">' + esc(entry.actionLabel) + '</span>' +
        '</div>' +
        '<div class="history-description">' + esc(entry.description) + '</div>' +
        '<div style="font-size:12px;opacity:0.6;margin-top:4px;">' + esc(entry.details) + '</div>' +
        '</div>';
    });

    historyList.innerHTML = html;

    // Обработчики кликов
    document.querySelectorAll('.history-item').forEach(function (item) {
      item.addEventListener('click', function () {
        var result;
        try { result = JSON.parse(this.getAttribute('data-result')); } catch (e) { result = {}; }
        showResultModal(result, this.getAttribute('data-type') || 'summary');
      });
    });
  }

  function showResultModal(result, actionType) {
    var html = '';
    currentResultText = '';

    if (actionType === 'tts' && result.audio_url) {
      html =
        '<div style="text-align:center;padding:20px;">' +
        '<p>🎧 <strong>' + esc(result.topic || 'Аудиопересказ') + '</strong></p>' +
        '<audio controls style="width:100%;margin-top:16px;">' +
        '<source src="' + result.audio_url + '" type="audio/mpeg">' +
        'Ваш браузер не поддерживает аудио' +
        '</audio>' +
        '</div>';
      currentResultText = 'Аудиопересказ: ' + (result.topic || '');
    } else if (actionType === 'chronology' && result.chronology_path) {
      // Пытаемся загрузить файл хронологии
      html =
        '<div style="padding:20px;">' +
        '<p>📅 <strong>' + esc(result.topic || 'Хронология') + '</strong></p>' +
        '<p style="font-size:13px;opacity:0.6;">Файл хронологии сохранён на сервере.</p>' +
        '<button onclick="window.location.href=\'/main/\'" class="btn btn-primary btn-sm" style="margin-top:12px;">Перейти к кластеру #' + result.cluster_id + '</button>' +
        '</div>';
      currentResultText = 'Хронология: ' + (result.topic || '');
    } else if (actionType === 'plot') {
      html =
        '<div style="text-align:center;padding:20px;">' +
        '<p>📈 <strong>' + esc(result.topic || 'График кластера') + '</strong></p>' +
        '<button id="reopenPlotBtn" class="btn btn-primary" style="margin-top:12px;">Открыть график</button>' +
        '</div>';
      currentResultText = 'График: ' + (result.topic || '');
      // Отложенное добавление обработчика
      setTimeout(function () {
        var btn = document.getElementById('reopenPlotBtn');
        if (btn) {
          btn.addEventListener('click', function () {
            window.open('/api/clusters/' + result.cluster_id + '/plot', '_blank');
          });
        }
      }, 100);
    } else if (actionType === 'search') {
      html =
        '<div style="padding:20px;">' +
        '<p>🔍 <strong>Поиск по новостям</strong></p>' +
        '<p>Связан с кластером: <strong>' + esc(result.topic || '#' + result.cluster_id) + '</strong></p>' +
        '<button onclick="window.location.href=\'/main/\'" class="btn btn-primary btn-sm" style="margin-top:12px;">Перейти к поиску</button>' +
        '</div>';
      currentResultText = 'Поиск: ' + (result.topic || '');
    } else if (result.topic) {
      html =
        '<div class="result-cluster">' +
        '<div class="result-cluster-title">' + esc(result.topic) + '</div>' +
        '<div class="result-cluster-summary" style="margin-top:12px;">' + esc(result.summary || 'Нет саммари') + '</div>' +
        '<div class="result-cluster-sources" style="margin-top:8px;">📡 Источники: ' + esc((result.sources || []).join(', ')) + '</div>' +
        '<button id="reRunBtn" class="btn btn-primary btn-sm" style="margin-top:12px;">🔄 Повторить с теми же параметрами</button>' +
        '</div>';
      currentResultText = (result.topic || '') + '\n' + (result.summary || '');
      // Обработчик повтора
      setTimeout(function () {
        var btn = document.getElementById('reRunBtn');
        if (btn) {
          btn.addEventListener('click', function () {
            window.location.href = '/main/';
          });
        }
      }, 100);
    } else {
      html = '<div>Нет данных</div>';
    }

    modalBody.innerHTML = html;
    resultModal.classList.remove('hidden');
  }

  // ─── Очистить историю ───────────────────────────────────────
  document.getElementById('clearHistoryBtn').addEventListener('click', function () {
    if (!confirm('Вы уверены, что хотите удалить ВСЕ записи истории? Это действие необратимо.')) {
      return;
    }

    var btn = this;
    btn.disabled = true;
    btn.textContent = '⏳ Удаление...';

    fetch('/api/clusters/history', {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      if (!resp.ok) throw new Error('Ошибка');
      return resp.json();
    })
    .then(function (data) {
      showToast(data.message || 'История очищена', 'success');
      loadHistory();
    })
    .catch(function (err) {
      showToast(err.message, 'error');
    })
    .finally(function () {
      btn.disabled = false;
      btn.textContent = '🗑️ Очистить историю';
    });
  });

  loadHistory();
});
