// main.js — полная версия (ES5-совместимый синтаксис)
console.log('main.js: ПЕРВАЯ СТРОКА');

// Каналы по умолчанию (разделены по источникам)
var DEFAULT_CHANNELS = [
  { name: 'ТАСС',        source: 'tg', tg_user: 'tass_agency' },
  { name: 'РБК',         source: 'tg', tg_user: 'rbc' },
  { name: 'Пул N3',      source: 'tg', tg_user: 'pool_n3' },
  { name: 'Lenta.ru',    source: 'lenta' },
  { name: 'Интерфакс',   source: 'tg', tg_user: 'interfax' },
  { name: 'Коммерсантъ', source: 'tg', tg_user: 'kommersant' },
];

document.addEventListener('DOMContentLoaded', function () {
  console.log('main.js: DOMContentLoaded СТАРТ');

  // ─── Проверка авторизации ──────────────────────────────────
  var token = getToken();
  console.log('main.js: token =', token ? token.slice(0, 10) + '...' : 'null');
  if (!token) {
    window.location.href = '/login/';
    return;
  }

  var role = getRole();
  document.getElementById('userRole').textContent = role === 'ADMIN' ? 'Администратор' : 'Пользователь';

  // ─── Элементы ──────────────────────────────────────────────
  var clusterSlider    = document.getElementById('clusterSlider');
  var clusterValue     = document.getElementById('clusterValue');
  var channelSearch    = document.getElementById('channelSearch');
  var channelsList     = document.getElementById('channelsList');
  var selectAllBtn     = document.getElementById('selectAllBtn');
  var clearAllBtn      = document.getElementById('clearAllBtn');
  var saveSettingsBtn  = document.getElementById('saveSettingsBtn');
  var generateBtn      = document.getElementById('generateSummaryBtn');
  var listenBtn        = document.getElementById('listenSummaryBtn');
  var graphBtn         = document.getElementById('viewGraphBtn');
  var allGraphBtn      = document.getElementById('viewAllGraphBtn');
  var chronologyBtn    = document.getElementById('buildChronologyBtn');
  var historyBtn       = document.getElementById('historyBtn');
  var adminLink        = document.getElementById('adminLink');
  var resultArea       = document.getElementById('resultArea');

  var currentClusters  = [];
  var currentClusterId = null;
  var currentClusterNum = null;
  var allChannels      = DEFAULT_CHANNELS.slice(); // копия
  var globalSearch     = document.getElementById('globalSearch');
  var globalSearchBtn  = document.getElementById('globalSearchBtn');

  // ─── Админ-ссылка ──────────────────────────────────────────
  if (role === 'ADMIN') adminLink.classList.remove('hidden');
  adminLink.addEventListener('click', function () {
    window.location.href = '/admin/';
  });

  // ─── Выход ─────────────────────────────────────────────────
  document.getElementById('logoutBtn').addEventListener('click', logout);

  // ─── История ───────────────────────────────────────────────
  historyBtn.addEventListener('click', function () {
    window.location.href = '/history/';
  });

  // ─── Слайдер ───────────────────────────────────────────────
  clusterSlider.addEventListener('input', function () {
    clusterValue.textContent = this.value;
  });

  // ─── Экранирование HTML ────────────────────────────────────
  function esc(str) {
    if (!str) return '';
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  // ─── Отрисовка каналов с группировкой по источнику ─────────
  function renderChannels(channels, filterText) {
    var q = (filterText || '').toLowerCase().trim();
    var filtered = [];
    var i, ch;

    if (q) {
      for (i = 0; i < channels.length; i++) {
        ch = channels[i];
        if (ch.name.toLowerCase().indexOf(q) !== -1) {
          filtered.push(ch);
        }
      }
    } else {
      filtered = channels;
    }

    var tgChannels = [];
    var lentaChannels = [];
    for (i = 0; i < filtered.length; i++) {
      ch = filtered[i];
      if (ch.source === 'lenta') {
        lentaChannels.push(ch);
      } else {
        tgChannels.push(ch);
      }
    }

    channelsList.innerHTML = '';

    if (filtered.length === 0) {
      channelsList.innerHTML = '<p class="text-center" style="padding:12px;opacity:0.6;">Ничего не найдено</p>';
      return;
    }

    function renderGroup(title, group) {
      if (group.length === 0) return '';
      var html = '<div class="channel-group-title">' + title + '</div>';
      for (var j = 0; j < group.length; j++) {
        var ch2 = group[j];
        var safeName = ch2.name.replace(/\s/g, '_');
        var icon = ch2.source === 'tg' ? '📱' : '🌐';
        html += '<div class="channel-item">'
              + '<input type="checkbox" id="ch_' + safeName + '" value="' + esc(ch2.name) + '" data-source="' + ch2.source + '" data-tg-user="' + (ch2.tg_user || '') + '" checked>'
              + '<label for="ch_' + safeName + '">'
              + '<span class="channel-source-icon">' + icon + '</span> '
              + esc(ch2.name)
              + '</label>'
              + '</div>';
      }
      return html;
    }

    var tgHtml   = renderGroup('📱 Telegram', tgChannels);
    var lentaHtml = renderGroup('🌐 Lenta.ru', lentaChannels);

    if (tgHtml) channelsList.insertAdjacentHTML('beforeend', tgHtml);
    if (lentaHtml) channelsList.insertAdjacentHTML('beforeend', lentaHtml);
  }

  // ─── Загрузка каналов с сервера (фоном) ────────────────────
  function loadChannelsFromServer() {
    fetch('/api/news/sources', {
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      if (!resp.ok) return;
      return resp.json();
    })
    .then(function (data) {
      if (!data) return;
      var serverChannels = Array.isArray(data) ? data : (data.sources || []);
      if (serverChannels.length > 0) {
        // Очищаем и пересоздаём список каналов (чтобы избежать дубликатов)
        allChannels = [];
        for (var i = 0; i < serverChannels.length; i++) {
          var name = serverChannels[i];
          var source = name.toLowerCase().indexOf('lenta') !== -1 ? 'lenta' : 'tg';
          // Ищем tg_user в DEFAULT_CHANNELS (по name или tg_user)
          var tgUser = '';
          for (var d = 0; d < DEFAULT_CHANNELS.length; d++) {
            if (DEFAULT_CHANNELS[d].name === name || DEFAULT_CHANNELS[d].tg_user === name) {
              tgUser = DEFAULT_CHANNELS[d].tg_user || '';
              // Если нашли по tg_user — используем красивое имя
              name = DEFAULT_CHANNELS[d].name;
              break;
            }
          }
          allChannels.push({ name: name, source: source, tg_user: tgUser });
        }
        // Добавляем Lenta.ru если её нет
        var hasLenta = false;
        for (var j = 0; j < allChannels.length; j++) {
          if (allChannels[j].name === 'Lenta.ru') { hasLenta = true; break; }
        }
        if (!hasLenta) {
          allChannels.push({ name: 'Lenta.ru', source: 'lenta', tg_user: '' });
        }
        renderChannels(allChannels, channelSearch.value);
      }
    })
    .catch(function () {});
  }

  // ─── Поиск по каналам ──────────────────────────────────────
  channelSearch.addEventListener('input', function () {
    renderChannels(allChannels, this.value);
  });

  // ─── Выбрать всё / Снять всё ───────────────────────────────
  selectAllBtn.addEventListener('click', function () {
    var cbs = channelsList.querySelectorAll('input[type="checkbox"]');
    for (var i = 0; i < cbs.length; i++) cbs[i].checked = true;
  });
  clearAllBtn.addEventListener('click', function () {
    var cbs = channelsList.querySelectorAll('input[type="checkbox"]');
    for (var i = 0; i < cbs.length; i++) cbs[i].checked = false;
  });

  // ─── Сохранение настроек (на сервер) ──────────────────────
  saveSettingsBtn.addEventListener('click', function () {
    var clusterCount = parseInt(clusterSlider.value);
    var cbs = channelsList.querySelectorAll('input[type="checkbox"]:checked');
    var selected = [];
    for (var i = 0; i < cbs.length; i++) {
      selected.push({
        name: cbs[i].value,
        source: cbs[i].dataset.source || 'tg'
      });
    }

    if (selected.length === 0) {
      showToast('Выберите хотя бы один канал', 'error');
      return;
    }

    // Сохраняем локально
    localStorage.setItem('clusterCount', '' + clusterCount);
    localStorage.setItem('selectedChannels', JSON.stringify(selected));

    // Сохраняем на сервер
    var channelNames = [];
    for (var j = 0; j < selected.length; j++) {
      channelNames.push(selected[j].name);
    }

    fetch('/api/auth/settings', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + getToken(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        cluster_count: clusterCount,
        channels: channelNames
      })
    })
    .then(function (resp) {
      if (resp.ok) {
        showToast('Настройки сохранены (сервер + локально)', 'success');
      } else {
        showToast('Настройки сохранены локально', 'success');
      }
    })
    .catch(function () {
      showToast('Настройки сохранены локально', 'success');
    });
  });

  // ─── Помощник: если 401 — токен истёк, просим перелогиниться ──
  function handleAuthError(resp) {
    if (resp.status === 401) {
      showToast('Сессия истекла. Войдите заново.', 'error');
      setTimeout(function () { logout(); }, 1500);
      return true;
    }
    return false;
  }

  // ─── Семантический поиск по кластерам ───────────────────────
  function doGlobalSearch(query) {
    if (!query) {
      showToast('Введите запрос', 'error');
      return;
    }

    resultArea.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Семантический поиск...</p></div>';
    var url = '/api/clusters/search?q=' + encodeURIComponent(query) + '&limit=15';

    fetch(url, {
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      if (handleAuthError(resp)) return null;
      if (!resp.ok) {
        return resp.json().then(function (errData) {
          throw new Error(errData.detail || 'Сервер: HTTP ' + resp.status);
        }).catch(function (parseErr) {
          if (parseErr.message && parseErr.message.indexOf('Сервер:') === 0) throw parseErr;
          throw new Error('Ошибка поиска (HTTP ' + resp.status + ')');
        });
      }
      return resp.json();
    })
    .then(function (data) {
      if (!data) return;
      var clusters = data.clusters || [];

      if (clusters.length === 0) {
        resultArea.innerHTML = '<div class="text-center" style="padding:40px;">😕 Ничего не найдено по запросу «' + esc(query) + '»</div>';
        return;
      }

      var html = '<h2>🔍 Результаты семантического поиска: «' + esc(query) + '»</h2>'
               + '<p style="margin-bottom:16px;">Найдено кластеров: ' + clusters.length + '</p>';

      for (var i = 0; i < clusters.length; i++) {
        var c = clusters[i];
        var simPercent = Math.round((c.similarity || 0) * 100);
        var dateStr = '';
        if (c.date_from && c.date_to) {
          dateStr = c.date_from === c.date_to ? c.date_from : (c.date_from + ' — ' + c.date_to);
        } else {
          dateStr = (c.created_at || '').slice(0, 10);
        }

        html += '<div class="cluster-card" data-id="' + c.cluster_id + '" data-num="' + (i+1) + '" onclick="window._selectCluster(this, ' + c.cluster_id + ', ' + (i+1) + ')">'
              + '<div class="cluster-header" onclick="event.stopPropagation(); window._toggleCluster(this)">'
              + '<span class="cluster-title">' + esc(c.cluster_title || c.topic) + '</span>'
              + '<span class="cluster-count">Сходство: ' + simPercent + '%</span>'
              + '</div>'
              + '<div class="cluster-body">'
              + '<div class="cluster-summary">' + esc(c.summary) + '</div>'
              + '<div class="cluster-sources">📡 Источники: ' + esc((c.news_sources || []).join(', ')) + '</div>'
              + '<div class="cluster-news-count">📅 ' + dateStr + '</div>'
              + '</div>'
              + '</div>';
      }

      resultArea.innerHTML = html;
    })
    .catch(function (err) {
      resultArea.innerHTML = '<div class="text-center" style="padding:40px;color:var(--error);">⚠️ ' + esc(err.message) + '</div>';
    });
  }

  globalSearchBtn.addEventListener('click', function () {
    doGlobalSearch(globalSearch.value.trim());
  });

  globalSearch.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      doGlobalSearch(globalSearch.value.trim());
    }
  });

  // ─── Генерация саммари ─────────────────────────────────────
  generateBtn.addEventListener('click', function () {
    var dateFrom = document.getElementById('dateFrom').value;
    var dateTo   = document.getElementById('dateTo').value;

    if (!dateFrom || !dateTo) {
      showToast('Выберите период', 'error');
      return;
    }

    // Собираем выбранные каналы
    var selectedChannels = [];
    var cbs = channelsList.querySelectorAll('input[type="checkbox"]:checked');
    for (var i = 0; i < cbs.length; i++) {
      selectedChannels.push({
        name: cbs[i].value,
        source: cbs[i].dataset.source || 'tg',
        tg_user: cbs[i].dataset.tgUser || ''
      });
    }

    var clusterCount = parseInt(clusterSlider.value);

    resultArea.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Идёт кластеризация новостей...</p></div>';
    generateBtn.disabled = true;

    var url = '/api/clusters/cluster?k=' + clusterCount
      + '&date_from=' + encodeURIComponent(dateFrom)
      + '&date_to=' + encodeURIComponent(dateTo)
      + '&channels=' + encodeURIComponent(JSON.stringify(selectedChannels));

    // Таймер
    var startTime = Date.now();
    var timerId = setInterval(function () {
      var elapsed = Math.floor((Date.now() - startTime) / 1000);
      resultArea.innerHTML = '<div class="loading">'
        + '<div class="loading-spinner"></div>'
        + '<p>Идёт обработка... ' + elapsed + ' сек</p>'
        + '</div>';
    }, 500);

    fetch(url, {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      clearInterval(timerId);
      if (!resp.ok) {
        return resp.json().then(function (errData) {
          throw new Error(errData.detail || ('HTTP ' + resp.status));
        });
      }
      return resp.json();
    })
    .then(function (data) {
      currentClusters = data.clusters || [];
      var totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
      resultArea.innerHTML = '<h2>Результаты кластеризации <span style="font-size:14px;font-weight:400;opacity:0.6;">(заняло ' + totalTime + ' сек)</span></h2>';

      if (data.warning) {
        showToast(data.warning, 'warning');
      }

      if (currentClusters.length === 0) {
        resultArea.innerHTML += '<div class="text-center" style="padding:40px;">Нет новостей для кластеризации.</div>';
        showToast('Нет данных', 'warning');
        return;
      }
      renderClusters(currentClusters);
      listenBtn.disabled = false;
      showToast('Саммари: ' + currentClusters.length + ' кластеров', 'success');
    })
    .catch(function (err) {
      resultArea.innerHTML = '<div class="text-center" style="padding:40px;color:var(--error);">⚠️ ' + esc(err.message) + '</div>';
      showToast(err.message, 'error');
    })
    .finally(function () {
      generateBtn.disabled = false;
    });
  });

  // ─── Кнопка "Загрузить Telegram" ───────────────────────────
  document.getElementById('loadTgBtn').addEventListener('click', function () {
    var input = document.getElementById('tgChannelInput');
    var channel = input.value.trim();
    if (!channel) {
      showToast('Введите название канала', 'error');
      return;
    }

    var btn = this;
    btn.disabled = true;
    btn.textContent = '⏳ Загрузка...';

    fetch('/api/parser/tg', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + getToken(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ channel: channel })
    })
    .then(function (resp) {
      if (handleAuthError(resp)) return null;
      if (!resp.ok) {
        return resp.json().then(function (e) { throw new Error(e.detail || 'Ошибка'); });
      }
      return resp.json();
    })
    .then(function (data) {
      if (!data) return;
      showToast(data.message || 'Загружено', 'success');
      loadChannelsFromServer();
    })
    .catch(function (err) {
      showToast(err.message, 'error');
    })
    .finally(function () {
      btn.disabled = false;
      btn.textContent = 'Загрузить';
    });
  });

  // ─── TTS ───────────────────────────────────────────────────
  listenBtn.addEventListener('click', function () {
    if (!currentClusterId) {
      showToast('Выберите кластер', 'error');
      return;
    }
    listenBtn.disabled = true;
    listenBtn.textContent = '⏳ Генерация...';

    fetch('/api/clusters/' + currentClusterId + '/tts', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      if (!resp.ok) {
        return resp.json().then(function (e) { throw new Error(e.detail || 'Ошибка TTS'); });
      }
      return resp.json();
    })
    .then(function (data) {
      showToast('Аудио создано', 'success');
      if (data && data.audio_url) {
        // Останавливаем все предыдущие аудио
        var allAudio = document.querySelectorAll('.audio-player audio');
        for (var a = 0; a < allAudio.length; a++) {
          allAudio[a].pause();
          allAudio[a].currentTime = 0;
        }

        var num = currentClusterNum || currentClusterId;
        var playerHtml = '<div class="audio-player" style="margin-top:16px;padding:16px;background:var(--bg-primary);border-radius:12px;text-align:center;">'
          + '<p>🎧 Аудиопересказ кластера №' + num + '</p>'
          + '<audio controls style="width:100%;margin-top:8px;" autoplay>'
          + '<source src="' + data.audio_url + '" type="audio/mpeg">'
          + 'Ваш браузер не поддерживает аудио</audio>'
          + '</div>';
        var resultDiv = document.getElementById('resultArea');
        if (resultDiv) {
          resultDiv.insertAdjacentHTML('beforeend', playerHtml);
        }
      }
    })
    .catch(function (err) {
      showToast(err.message, 'error');
    })
    .finally(function () {
      listenBtn.disabled = false;
      listenBtn.textContent = '🎧 Сгенерировать аудио';
    });
  });

  // ─── График одного кластера ───────────────────────────────
  graphBtn.addEventListener('click', function () {
    if (!currentClusterId) { showToast('Выберите кластер', 'error'); return; }

    var btn = this;
    btn.disabled = true;
    btn.textContent = '⏳ Построение...';

    fetch('/api/clusters/' + currentClusterId + '/plot', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      if (!resp.ok) throw new Error('Ошибка');
      return resp.text();
    })
    .then(function (html) {
      // Открываем график в новой вкладке
      var win = window.open('', '_blank');
      if (win) {
        win.document.write(html);
        win.document.close();
      } else {
        showToast('Разрешите всплывающие окна для этого сайта', 'error');
      }
    })
    .catch(function (err) {
      showToast(err.message, 'error');
    })
    .finally(function () {
      btn.disabled = false;
      btn.textContent = '📈 График кластера';
    });
  });

  // ─── Карта всех кластеров ──────────────────────────────────
  allGraphBtn.addEventListener('click', function () {
    var btn = this;
    btn.disabled = true;
    btn.textContent = '⏳ Построение карты...';

    fetch('/api/clusters/plot', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      if (!resp.ok) {
        return resp.json().then(function (e) { throw new Error(e.detail || 'Ошибка'); });
      }
      return resp.text();
    })
    .then(function (html) {
      var win = window.open('', '_blank');
      if (win) {
        win.document.write(html);
        win.document.close();
      } else {
        showToast('Разрешите всплывающие окна для этого сайта', 'error');
      }
    })
    .catch(function (err) {
      showToast(err.message, 'error');
    })
    .finally(function () {
      btn.disabled = false;
      btn.textContent = '🗺️ Карта всех кластеров';
    });
  });

  // ─── Хронология ────────────────────────────────────────────
  chronologyBtn.addEventListener('click', function () {
    if (!currentClusterId) { showToast('Выберите кластер', 'error'); return; }

    var btn = this;
    btn.disabled = true;
    btn.textContent = '⏳ Построение хронологии...';

    resultArea.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Строю хронологию...</p></div>';

    fetch('/api/clusters/' + currentClusterId + '/chronology', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      if (!resp.ok) {
        return resp.json().then(function (e) { throw new Error(e.detail || 'Ошибка'); });
      }
      return resp.json();
    })
    .then(function (data) {
      if (!data || !data.success) {
        throw new Error(data && data.error ? data.error : 'Неизвестная ошибка');
      }

      var chronology = data.chronology || '';
      var clusterId = data.cluster_id;
      var clusterNum = currentClusterNum || clusterId;

      var html = '<h2>📅 Хронология событий (кластер №' + clusterNum + ')</h2>'
               + '<div class="chronology-text" style="background:var(--bg-primary);padding:20px;border-radius:12px;margin-top:16px;white-space:pre-wrap;font-family:monospace;line-height:1.8;">'
               + esc(chronology)
               + '</div>'
               + '<p style="margin-top:12px;font-size:12px;opacity:0.6;">💾 Сохранено в data/' + getRole() + '/</p>';

      resultArea.innerHTML = html;
      showToast('Хронология построена', 'success');
    })
    .catch(function (err) {
      resultArea.innerHTML = '<div class="text-center" style="padding:40px;color:var(--error);">⚠️ ' + esc(err.message) + '</div>';
      showToast(err.message, 'error');
    })
    .finally(function () {
      btn.disabled = false;
      btn.textContent = '📅 Хронология';
    });
  });

  // ─── Отрисовка кластеров ───────────────────────────────────
  function renderClusters(clusters) {
    var html = '<h2>Результаты кластеризации</h2>';

    for (var i = 0; i < clusters.length; i++) {
      var cluster = clusters[i];
      var dateStr = '';
      if (cluster.date_from && cluster.date_to) {
        dateStr = cluster.date_from === cluster.date_to ? cluster.date_from : (cluster.date_from + ' — ' + cluster.date_to);
      } else {
        dateStr = (cluster.created_at || '').slice(0, 10);
      }
      var count = cluster.news_count || '';
      var sources = (cluster.news_sources || []).join(', ');

      html += '<div class="cluster-card" data-id="' + cluster.cluster_id + '" data-num="' + (i+1) + '" onclick="window._selectCluster(this, ' + cluster.cluster_id + ', ' + (i+1) + ')">'
            + '<div class="cluster-header" onclick="event.stopPropagation(); window._toggleCluster(this)">'
            + '<span class="cluster-title">Кластер ' + (i+1) + ': ' + esc(cluster.cluster_title || cluster.topic) + '</span>'
            + '<span class="cluster-count">' + dateStr + '</span>'
            + '</div>'
            + '<div class="cluster-body">'
            + '<div class="cluster-summary">' + esc(cluster.summary) + '</div>'
            + '<div class="cluster-sources">📡 Источники: ' + esc(sources) + '</div>'
            + (count ? '<div class="cluster-news-count">📰 Новостей в кластере: <strong>' + count + '</strong></div>' : '')
            + '<button class="btn btn-outline btn-sm copy-cluster-btn" style="margin-top:8px;" onclick="event.stopPropagation(); window._copyCluster(' + cluster.cluster_id + ')" title="Копировать текст">📋 Копировать</button>'
            + '</div>'
            + '</div>';
    }

    resultArea.innerHTML = html;
  }

  window._selectCluster = function (el, clusterId, clusterNum) {
    var cards = document.querySelectorAll('.cluster-card');
    for (var i = 0; i < cards.length; i++) cards[i].classList.remove('cluster-selected');
    el.classList.add('cluster-selected');
    currentClusterId = clusterId;
    currentClusterNum = clusterNum || parseInt(el.dataset.num) || clusterId;
    listenBtn.disabled = false;
    graphBtn.disabled = false;
    chronologyBtn.disabled = false;
  };
  window._toggleCluster = function (header) {
    header.closest('.cluster-card').classList.toggle('cluster-collapsed');
  };
  window._copyCluster = function (clusterId) {
    var card = document.querySelector('.cluster-card[data-id="' + clusterId + '"]');
    if (!card) return;
    var title = card.querySelector('.cluster-title');
    var summary = card.querySelector('.cluster-summary');
    var sources = card.querySelector('.cluster-sources');
    var text = (title ? title.textContent : '') + '\n\n'
             + (summary ? summary.textContent : '') + '\n\n'
             + (sources ? sources.textContent : '');
    navigator.clipboard.writeText(text).then(function () {
      showToast('Текст скопирован', 'success');
    }).catch(function () {
      showToast('Не удалось скопировать', 'error');
    });
  };

  // ─── Настройки по умолчанию ────────────────────────────────
  function loadSavedSettings() {
    var saved = localStorage.getItem('clusterCount');
    if (saved) {
      clusterSlider.value = saved;
      clusterValue.textContent = saved;
    }

    // Загружаем с сервера (перезаписывает локальные, если доступны)
    fetch('/api/auth/settings', {
      headers: { 'Authorization': 'Bearer ' + getToken() }
    })
    .then(function (resp) {
      if (!resp.ok) return;
      return resp.json();
    })
    .then(function (data) {
      if (data && data.cluster_count) {
        clusterSlider.value = data.cluster_count;
        clusterValue.textContent = data.cluster_count;
        localStorage.setItem('clusterCount', '' + data.cluster_count);
      }
    })
    .catch(function () {});
  }

  function setDefaultDates() {
    var today = new Date();
    var weekAgo = new Date();
    weekAgo.setDate(today.getDate() - 7);
    document.getElementById('dateTo').value   = today.toISOString().split('T')[0];
    document.getElementById('dateFrom').value = weekAgo.toISOString().split('T')[0];
  }

  // ─── Инициализация ─────────────────────────────────────────
  loadSavedSettings();
  setDefaultDates();
  renderChannels(allChannels, '');          // сразу показываем каналы
  loadChannelsFromServer();                 // пробуем обновить с сервера
});
