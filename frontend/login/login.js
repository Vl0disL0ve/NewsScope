// login.js

document.addEventListener('DOMContentLoaded', function() {
      const form = document.getElementById('loginForm');
      const telegramCheckbox = document.getElementById  ('telegramMode');
      const telegramIdGroup = document.getElementById   ('telegramIdGroup');
      let failedAttempts = parseInt(localStorage.getItem('failedAttempts') || '0');
      const blockedUntil = localStorage.getItem('blockedUntil');

      // Если есть блокировка
      if (blockedUntil && Date.now() < parseInt(blockedUntil)) {
        const remaining = Math.ceil((parseInt(blockedUntil) -   Date.now()) / 1000 / 60);
        showToast('Доступ заблокирован на ' + remaining + ' минут', 'error');
        document.querySelector('button[type="submit"]').disabled= true;
      }

      // Показать/скрыть поле Telegram ID
      telegramCheckbox.addEventListener('change', function(e) {
        if (e.target.checked) {
          telegramIdGroup.classList.remove('hidden');
        } else {
          telegramIdGroup.classList.add('hidden');
        }
      });

      // Отправка формы
      form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Проверка блокировки
        const blockedUntilTime = localStorage.getItem   ('blockedUntil');
        if (blockedUntilTime && Date.now() < parseInt   (blockedUntilTime)) {
          showToast('Вход временно заблокирован', 'error');
          return;
        }

        const login = document.getElementById('login').value;
        const password = document.getElementById('password').   value;
        const useTelegram = telegramCheckbox.checked;
        const telegramId = useTelegram ? document.getElementById('telegramId').value : null;

        // ===== ВРЕМЕННЫЙ МОК (потом заменишь на реальный API) =====
        if (login === 'admin' && password === 'admin') {
          saveToken('mock-token-admin');
          saveRole('ADMIN');
          localStorage.removeItem('failedAttempts');
          localStorage.removeItem('blockedUntil');
          window.location.href = '/main/';
        } 
        else if (login === 'user' && password === 'user') {
          saveToken('mock-token-user');
          saveRole('USER');
          localStorage.removeItem('failedAttempts');
          localStorage.removeItem('blockedUntil');
          window.location.href = '/main/';
        }
        else {
          failedAttempts++;
          localStorage.setItem('failedAttempts', failedAttempts);

          if (failedAttempts >= 5) {
            const blockUntil = Date.now() + 15 * 60 * 1000;
            localStorage.setItem('blockedUntil', blockUntil);
            showToast('Превышено количество попыток. Блокировка 15 минут', 'error');
            document.querySelector('button[type="submit"]').disabled = true;
          } else {
            const remaining = 5 - failedAttempts;
            showToast('Неверный логин или пароль. Осталось  попыток: ' + remaining, 'error');
          }
        }
      });
});