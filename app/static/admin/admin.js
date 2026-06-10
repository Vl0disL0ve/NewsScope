// admin.js — админ-панель с интерактивными графиками Plotly

document.addEventListener('DOMContentLoaded', function () {
  const token = getToken();
  const role = getRole();

  if (!token) { window.location.href = '/login/'; return; }
  if (role !== 'ADMIN') {
    showToast('Доступ запрещён', 'error');
    setTimeout(function () { window.location.href = '/main/'; }, 1500);
    return;
  }

  document.getElementById('userRole').textContent = 'Администратор';
  document.getElementById('logoutBtn').addEventListener('click', logout);
  document.getElementById('backToMainBtn').addEventListener('click', function () {
    window.location.href = '/main/';
  });

  function authHeaders() {
    return { 'Authorization': 'Bearer ' + getToken(), 'Content-Type': 'application/json' };
  }

  function esc(str) {
    if (!str) return '';
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  // ─────────────────────────────────────────────────────────────
  // 1. ВЫДАЧА ПРАВ
  // ─────────────────────────────────────────────────────────────
  var addUserBtn = document.getElementById('addUserBtn');
  var newLogin = document.getElementById('newLogin');
  var newPassword = document.getElementById('newPassword');
  var addUserMessage = document.getElementById('addUserMessage');

  addUserBtn.addEventListener('click', async function () {
    var login = newLogin.value.trim();
    var password = newPassword.value.trim();
    if (!login || !password) {
      addUserMessage.innerHTML = '<span style="color: var(--danger);">Заполните оба поля</span>';
      return;
    }
    addUserBtn.disabled = true;
    addUserMessage.innerHTML = '<span>Регистрация...</span>';
    try {
      var resp = await fetch('/api/auth/register', {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ login: login, password: password, role: 'user' })
      });
      var data = await resp.json();
      if (!resp.ok) {
        addUserMessage.innerHTML = '<span style="color: var(--danger);">' + esc(data.detail || 'Ошибка') + '</span>';
        return;
      }
      addUserMessage.innerHTML = '<span style="color: var(--success);">✅ Добавлен: ' + esc(login) + '</span>';
      newLogin.value = '';
      newPassword.value = '';
    } catch (err) {
      addUserMessage.innerHTML = '<span style="color: var(--danger);">Ошибка соединения</span>';
    } finally {
      addUserBtn.disabled = false;
    }
  });

  // ─────────────────────────────────────────────────────────────
  // 2. СТАТИСТИКА ПОСЕЩЕНИЙ
  // ─────────────────────────────────────────────────────────────
  var visitInterval = document.getElementById('visitInterval');
  var customVisitRange = document.getElementById('customVisitRange');
  var loadVisitStatsBtn = document.getElementById('loadVisitStatsBtn');
  var visitStatsResult = document.getElementById('visitStatsResult');
  var visitUserSelect = document.getElementById('visitUserSelect');
  var searchUserGroup = document.getElementById('searchUserGroup');
  var searchUserLogin = document.getElementById('searchUserLogin');

  visitInterval.addEventListener('change', function () {
    customVisitRange.classList.toggle('hidden', this.value !== 'custom');
  });

  visitUserSelect.addEventListener('change', function () {
    searchUserGroup.classList.toggle('hidden', this.value !== 'search');
  });

  loadVisitStatsBtn.addEventListener('click', async function () {
    var interval = visitInterval.value;
    var url = '/api/admin/stats/visits?interval=' + interval;

    if (interval === 'custom') {
      var customDates = document.getElementById('customVisitDates').value;
      var parts = customDates.split(' - ');
      if (parts.length === 2) {
        url += '&date_from=' + encodeURIComponent(parts[0]) + '&date_to=' + encodeURIComponent(parts[1]);
      }
    }

    // Поиск пользователя
    if (visitUserSelect.value === 'search') {
      var q = searchUserLogin.value.trim();
      if (q) {
        try {
          var uResp = await fetch('/api/admin/users/search?q=' + encodeURIComponent(q), { headers: authHeaders() });
          var users = await uResp.json();
          if (users.length > 0) {
            url += '&user_id=' + users[0].user_id;
          }
        } catch (e) {}
      }
    }

    visitStatsResult.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Загрузка...</p></div>';

    try {
      var resp = await fetch(url, { headers: authHeaders() });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      var data = await resp.json();

      if (!Array.isArray(data) || data.length === 0) {
        visitStatsResult.innerHTML = '<div class="empty-state">Нет данных за выбранный период</div>';
        return;
      }

      var labels = data.map(function (r) { return r.label; });
      var values = data.map(function (r) { return r.value; });
      var xTitle = interval === 'day' ? 'Час' : 'Дата';

      var trace = {
        x: labels, y: values,
        type: 'scatter', mode: 'lines+markers',
        marker: { color: '#4f46e5', size: 6 },
        line: { shape: 'spline', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(79, 70, 229, 0.1)',
      };

      var layout = {
        title: 'Посещения (' + (interval === 'day' ? 'по часам' : 'по дням') + ')',
        xaxis: { title: xTitle, tickangle: -45 },
        yaxis: { title: 'Количество входов' },
        template: 'plotly_white',
        height: 350,
        margin: { t: 40, r: 20, b: 80, l: 60 },
      };

      Plotly.newPlot(visitStatsResult, [trace], layout, { responsive: true });
    } catch (err) {
      visitStatsResult.innerHTML = '<div style="padding:20px;color:var(--error);">⚠️ ' + esc(err.message) + '</div>';
    }
  });

  // ─────────────────────────────────────────────────────────────
  // 3. СТАТИСТИКА НОВЫХ ПОЛЬЗОВАТЕЛЕЙ
  // ─────────────────────────────────────────────────────────────
  var newUsersInterval = document.getElementById('newUsersInterval');
  var customNewUsersRange = document.getElementById('customNewUsersRange');
  var loadNewUsersStatsBtn = document.getElementById('loadNewUsersStatsBtn');
  var newUsersStatsResult = document.getElementById('newUsersStatsResult');

  newUsersInterval.addEventListener('change', function () {
    customNewUsersRange.classList.toggle('hidden', this.value !== 'custom');
  });

  loadNewUsersStatsBtn.addEventListener('click', async function () {
    var interval = newUsersInterval.value;
    var url = '/api/admin/stats/users?interval=' + interval;

    if (interval === 'custom') {
      var customDates = document.getElementById('customNewUsersDates').value;
      var parts = customDates.split(' - ');
      if (parts.length === 2) {
        url += '&date_from=' + encodeURIComponent(parts[0]) + '&date_to=' + encodeURIComponent(parts[1]);
      }
    }

    newUsersStatsResult.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Загрузка...</p></div>';

    try {
      var resp = await fetch(url, { headers: authHeaders() });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      var data = await resp.json();

      if (!Array.isArray(data) || data.length === 0) {
        newUsersStatsResult.innerHTML = '<div class="empty-state">Нет данных за выбранный период</div>';
        return;
      }

      var labels = data.map(function (r) { return r.label; });
      var values = data.map(function (r) { return r.value; });

      var trace = {
        x: labels, y: values,
        type: 'bar',
        marker: { color: '#10b981', opacity: 0.8 },
      };

      var layout = {
        title: 'Новые пользователи',
        xaxis: { title: 'Дата', tickangle: -45 },
        yaxis: { title: 'Количество регистраций' },
        template: 'plotly_white',
        height: 350,
        margin: { t: 40, r: 20, b: 80, l: 60 },
      };

      Plotly.newPlot(newUsersStatsResult, [trace], layout, { responsive: true });
    } catch (err) {
      newUsersStatsResult.innerHTML = '<div style="padding:20px;color:var(--error);">⚠️ ' + esc(err.message) + '</div>';
    }
  });

  // ─────────────────────────────────────────────────────────────
  // 4. СТАТИСТИКА БД
  // ─────────────────────────────────────────────────────────────
  var loadDbStatsBtn = document.getElementById('loadDbStatsBtn');
  var dbStatsResult = document.getElementById('dbStatsResult');

  loadDbStatsBtn.addEventListener('click', async function () {
    dbStatsResult.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Загрузка...</p></div>';

    try {
      var resp = await fetch('/api/admin/stats/database', { headers: authHeaders() });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      var data = await resp.json();

      dbStatsResult.innerHTML =
        '<div class="db-stats-card">' +
        '<div class="db-stat-item"><div class="db-stat-value">' + (data.users || 0) + '</div><div class="db-stat-label">Пользователей</div></div>' +
        '<div class="db-stat-item"><div class="db-stat-value">' + (data.news || 0) + '</div><div class="db-stat-label">Новостей</div></div>' +
        '<div class="db-stat-item"><div class="db-stat-value">' + (data.clusters || 0) + '</div><div class="db-stat-label">Кластеров</div></div>' +
        '<div class="db-stat-item"><div class="db-stat-value">' + (data.actions || 0) + '</div><div class="db-stat-label">Действий</div></div>' +
        '</div>' +
        '<div style="display:flex;gap:20px;margin-top:20px;flex-wrap:wrap;">' +
        '<div style="flex:1;min-width:150px;background:var(--bg-primary);padding:16px;border-radius:12px;text-align:center;">' +
        '<div style="font-size:28px;font-weight:700;color:var(--accent);">' + (data.user_data_mb || 0) + ' МБ</div>' +
        '<div style="font-size:12px;opacity:0.6;">Польз. данные</div>' +
        '</div>' +
        '<div style="flex:1;min-width:150px;background:var(--bg-primary);padding:16px;border-radius:12px;text-align:center;">' +
        '<div style="font-size:28px;font-weight:700;color:var(--success);">' + (data.disk_free_gb || 0) + ' ГБ</div>' +
        '<div style="font-size:12px;opacity:0.6;">Свободно из ' + (data.disk_total_gb || 0) + ' ГБ</div>' +
        '</div>' +
        '</div>';
    } catch (err) {
      dbStatsResult.innerHTML = '<div style="padding:20px;color:var(--error);">⚠️ ' + esc(err.message) + '</div>';
    }
  });
});
