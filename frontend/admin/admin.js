// admin.js

document.addEventListener('DOMContentLoaded', function() {
  // Проверка авторизации и прав
  const token = getToken();
  const role = getRole();
  
  if (!token) {
    window.location.href = '/login/';
    return;
  }
  
  if (role !== 'ADMIN') {
    showToast('Доступ запрещён. Требуются права администратора', 'error');
    setTimeout(() => {
      window.location.href = '/main/';
    }, 1500);
    return;
  }
  
  document.getElementById('userRole').textContent = 'Администратор';
  
  // Кнопка выхода
  document.getElementById('logoutBtn').addEventListener('click', logout);
  
  // Кнопка "На главную"
  document.getElementById('backToMainBtn').addEventListener('click', function() {
    window.location.href = '/main/';
  });
  
  // ========== 1. ВЫДАЧА ПРАВ ==========
  const addUserBtn = document.getElementById('addUserBtn');
  const newLogin = document.getElementById('newLogin');
  const newPassword = document.getElementById('newPassword');
  const addUserMessage = document.getElementById('addUserMessage');
  
  addUserBtn.addEventListener('click', function() {
    const login = newLogin.value.trim();
    const password = newPassword.value.trim();
    
    if (!login || !password) {
      addUserMessage.innerHTML = '<span style="color: var(--danger);">Заполните оба поля</span>';
      return;
    }
    
    // TODO: реальный API вызов
    // МОК - проверка уникальности логина
    const existingUsers = ['admin', 'user', 'test'];
    if (existingUsers.includes(login)) {
      addUserMessage.innerHTML = '<span style="color: var(--danger);">Логин пользователя уже занят</span>';
      return;
    }
    
    // Успех
    addUserMessage.innerHTML = '<span style="color: var(--success);">✅ Пользователь добавлен</span>';
    newLogin.value = '';
    newPassword.value = '';
    setTimeout(() => {
      addUserMessage.innerHTML = '';
    }, 3000);
  });
  
  // ========== 2. СТАТИСТИКА ПОСЕЩЕНИЙ ==========
  const visitInterval = document.getElementById('visitInterval');
  const customVisitRange = document.getElementById('customVisitRange');
  const visitUserSelect = document.getElementById('visitUserSelect');
  const searchUserGroup = document.getElementById('searchUserGroup');
  const searchUserLogin = document.getElementById('searchUserLogin');
  const loadVisitStatsBtn = document.getElementById('loadVisitStatsBtn');
  const visitStatsResult = document.getElementById('visitStatsResult');
  
  // Показать/скрыть кастомный интервал
  visitInterval.addEventListener('change', function() {
    if (this.value === 'custom') {
      customVisitRange.classList.remove('hidden');
    } else {
      customVisitRange.classList.add('hidden');
    }
  });
  
  // Показать/скрыть поиск пользователя
  visitUserSelect.addEventListener('change', function() {
    if (this.value === 'search') {
      searchUserGroup.classList.remove('hidden');
    } else {
      searchUserGroup.classList.add('hidden');
    }
  });
  
  loadVisitStatsBtn.addEventListener('click', function() {
    const interval = visitInterval.value;
    let dateFrom = null;
    let dateTo = null;
    
    if (interval === 'custom') {
      const customDates = document.getElementById('customVisitDates').value;
      // Валидация формата (простая)
      const datePattern = /^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2} - \d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$/;
      if (!datePattern.test(customDates)) {
        showToast('Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ - ДД.ММ.ГГГГ ЧЧ:ММ', 'error');
        return;
      }
      const parts = customDates.split(' - ');
      dateFrom = parts[0];
      dateTo = parts[1];
    }
    
    let userId = null;
    if (visitUserSelect.value === 'search') {
      const login = searchUserLogin.value.trim();
      if (!login) {
        showToast('Введите логин пользователя', 'error');
        return;
      }
      userId = login; // TODO: реальный поиск по логину
    } else if (visitUserSelect.value !== 'all') {
      userId = visitUserSelect.value;
    }
    
    // МОК-ДАННЫЕ для графика
    visitStatsResult.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Загрузка статистики...</p></div>';
    
    setTimeout(function() {
      // TODO: реальный API
      visitStatsResult.innerHTML = `
        <div class="stats-graph-placeholder">
          📊 <strong>График посещений</strong><br>
          Интервал: ${interval}<br>
          Пользователь: ${userId || 'все'}<br>
          <div style="margin-top: 16px; padding: 20px; background: var(--white); border-radius: 8px;">
            [Здесь будет график]<br>
            Ось X: ${interval === 'day' ? 'часы' : 'дни'}<br>
            Ось Y: количество посещений
          </div>
        </div>
      `;
      showToast('Статистика загружена (демо-режим)', 'success');
    }, 800);
  });
  
  // ========== 3. СТАТИСТИКА НОВЫХ ПОЛЬЗОВАТЕЛЕЙ ==========
  const newUsersInterval = document.getElementById('newUsersInterval');
  const customNewUsersRange = document.getElementById('customNewUsersRange');
  const loadNewUsersStatsBtn = document.getElementById('loadNewUsersStatsBtn');
  const newUsersStatsResult = document.getElementById('newUsersStatsResult');
  
  newUsersInterval.addEventListener('change', function() {
    if (this.value === 'custom') {
      customNewUsersRange.classList.remove('hidden');
    } else {
      customNewUsersRange.classList.add('hidden');
    }
  });
  
  loadNewUsersStatsBtn.addEventListener('click', function() {
    const interval = newUsersInterval.value;
    
    newUsersStatsResult.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Загрузка...</p></div>';
    
    setTimeout(function() {
      newUsersStatsResult.innerHTML = `
        <div class="stats-graph-placeholder">
          📈 <strong>График новых пользователей</strong><br>
          Интервал: ${interval}<br>
          <div style="margin-top: 16px; padding: 20px; background: var(--white); border-radius: 8px;">
            [Здесь будет график]<br>
            Ось X: ${interval === 'day' ? 'часы' : 'дни'}<br>
            Ось Y: количество новых пользователей
          </div>
        </div>
      `;
      showToast('Статистика загружена (демо-режим)', 'success');
    }, 600);
  });
  
  // ========== 4. СТАТИСТИКА БД ==========
  const loadDbStatsBtn = document.getElementById('loadDbStatsBtn');
  const dbStatsResult = document.getElementById('dbStatsResult');
  
  loadDbStatsBtn.addEventListener('click', function() {
    dbStatsResult.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Загрузка...</p></div>';
    
    setTimeout(function() {
      // TODO: реальный API
      dbStatsResult.innerHTML = `
        <div class="db-stats-card">
          <div class="db-stat-item">
            <div class="db-stat-value">42</div>
            <div class="db-stat-label">Всего пользователей</div>
          </div>
          <div class="db-stat-item">
            <div class="db-stat-value">156.3 MB</div>
            <div class="db-stat-label">Пользовательские данные</div>
          </div>
          <div class="db-stat-item">
            <div class="db-stat-value">10 GB</div>
            <div class="db-stat-label">Общий объём сервера</div>
          </div>
        </div>
      `;
      showToast('Статистика БД загружена (демо-режим)', 'success');
    }, 500);
  });
});