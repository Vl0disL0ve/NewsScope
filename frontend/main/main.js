// main.js

document.addEventListener('DOMContentLoaded', function() {
  // Проверка авторизации
  const token = getToken();
  if (!token) {
    window.location.href = '/login/';
    return;
  }

  const role = getRole();
  document.getElementById('userRole').textContent = role === 'ADMIN' ? 'Администратор' : 'Пользователь';

  // Кнопка выхода
  document.getElementById('logoutBtn').addEventListener('click', logout);

  // Элементы
  const clusterSlider = document.getElementById('clusterSlider');
  const clusterValue = document.getElementById('clusterValue');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  const generateSummaryBtn = document.getElementById('generateSummaryBtn');
  const listenSummaryBtn = document.getElementById('listenSummaryBtn');
  const viewGraphBtn = document.getElementById('viewGraphBtn');
  const historyBtn = document.getElementById('historyBtn');
  const resultArea = document.getElementById('resultArea');

  // Текущее состояние
  let currentSummaryId = null;
  let currentSummaryText = null;

  // Обновление значения слайдера
  clusterSlider.addEventListener('input', function() {
    clusterValue.textContent = this.value;
  });

  // Загрузка списка каналов (мок)
  function loadChannels() {
    const channelsList = document.getElementById('channelsList');
    // TODO: заменить на реальный API
    const mockChannels = [
      { id: 1, name: 'ТАСС', selected: true },
      { id: 2, name: 'РБК', selected: true },
      { id: 3, name: 'Telegram-канал "Пул N3"', selected: true },
      { id: 4, name: 'Интерфакс', selected: false },
      { id: 5, name: 'Коммерсантъ', selected: false }
    ];
    
    channelsList.innerHTML = '';
    mockChannels.forEach(ch => {
      const div = document.createElement('div');
      div.className = 'channel-item';
      div.innerHTML = `
        <input type="checkbox" id="ch_${ch.id}" value="${ch.id}" ${ch.selected ? 'checked' : ''}>
        <label for="ch_${ch.id}">${ch.name}</label>
      `;
      channelsList.appendChild(div);
    });
  }

  // Сохранение настроек
  saveSettingsBtn.addEventListener('click', function() {
    const clusterCount = parseInt(clusterSlider.value);
    const selectedChannels = [];
    document.querySelectorAll('.channel-item input:checked').forEach(cb => {
      selectedChannels.push(parseInt(cb.value));
    });
    
    if (selectedChannels.length === 0) {
      showToast('Выберите хотя бы один канал', 'error');
      return;
    }
    
    // TODO: реальный API
    localStorage.setItem('clusterCount', clusterCount);
    localStorage.setItem('selectedChannels', JSON.stringify(selectedChannels));
    showToast('Настройки сохранены', 'success');
  });

  // Генерация саммари
  generateSummaryBtn.addEventListener('click', async function() {
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    
    if (!dateFrom || !dateTo) {
      showToast('Выберите период', 'error');
      return;
    }
    
    resultArea.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Идёт кластеризация...</p></div>';
    
    // TODO: реальный API
    setTimeout(() => {
      // МОК-ДАННЫЕ
      currentSummaryId = 'mock_' + Date.now();
      currentSummaryText = generateMockSummary();
      renderSummary(currentSummaryText);
      listenSummaryBtn.disabled = false;
      viewGraphBtn.disabled = false;
      showToast('Саммари готово', 'success');
    }, 1500);
  });

  // Озвучка
  listenSummaryBtn.addEventListener('click', function() {
    if (!currentSummaryId) {
      showToast('Сначала сделайте саммари', 'error');
      return;
    }
    // TODO: реальный TTS
    showToast('Озвучка временно недоступна (демо-режим)', 'warning');
  });

  // График
  viewGraphBtn.addEventListener('click', function() {
    if (!currentSummaryId) {
      showToast('Сначала сделайте саммари', 'error');
      return;
    }
    // TODO: реальный график
    showToast('График временно недоступен (демо-режим)', 'warning');
  });

  // История
  historyBtn.addEventListener('click', function() {
    window.location.href = '/history/';
  });

  // Мок-данные для саммари
  function generateMockSummary() {
    return {
      clusters: [
        {
          id: 1,
          topic: 'Международные переговоры',
          count: 38,
          summary: '15 марта в Женеве прошёл очередной раунд переговоров между делегациями России и США. Стороны обсудили вопросы экономического сотрудничества и международной безопасности. Достигнуты предварительные договорённости по ряду вопросов.',
          sources: ['ТАСС', 'РБК', 'Пул N3']
        },
        {
          id: 2,
          topic: 'Новые технологии в экономике',
          count: 24,
          summary: 'Российские компании активно внедряют технологии искусственного интеллекта в производственные процессы. Ожидается рост производительности на 15-20% в ближайшие два года. Эксперты отмечают позитивную динамику.',
          sources: ['Коммерсантъ', 'Интерфакс']
        },
        {
          id: 3,
          topic: 'Экологическая повестка',
          count: 15,
          summary: 'В России стартовала программа по снижению выбросов CO2. К 2030 году планируется сократить углеродный след на 30%. Крупные предприятия переходят на «зелёные» технологии.',
          sources: ['ТАСС', 'РБК']
        }
      ]
    };
  }

  function renderSummary(data) {
    let html = '<h2>Результаты кластеризации</h2>';
    data.clusters.forEach((cluster, idx) => {
      html += `
        <div class="cluster-card" data-cluster-idx="${idx}">
          <div class="cluster-header" onclick="toggleCluster(this)">
            <span class="cluster-title">Кластер ${idx+1}: ${cluster.topic}</span>
            <span class="cluster-count">${cluster.count} новостей</span>
          </div>
          <div class="cluster-body">
            <div class="cluster-summary">${cluster.summary}</div>
            <div class="cluster-sources">📡 Источники: ${cluster.sources.join(', ')}</div>
          </div>
        </div>
      `;
    });
    resultArea.innerHTML = html;
  }

  // Для сворачивания/разворачивания
  window.toggleCluster = function(header) {
    const card = header.closest('.cluster-card');
    card.classList.toggle('cluster-collapsed');
  };

  // Загрузить сохранённые настройки
  function loadSavedSettings() {
    const savedCluster = localStorage.getItem('clusterCount');
    if (savedCluster) {
      clusterSlider.value = savedCluster;
      clusterValue.textContent = savedCluster;
    }
  }

  // Установка дат по умолчанию (последние 7 дней)
  function setDefaultDates() {
    const today = new Date();
    const weekAgo = new Date();
    weekAgo.setDate(today.getDate() - 7);
    
    document.getElementById('dateTo').value = today.toISOString().split('T')[0];
    document.getElementById('dateFrom').value = weekAgo.toISOString().split('T')[0];
  }

  // Инициализация
  loadChannels();
  loadSavedSettings();
  setDefaultDates();
});