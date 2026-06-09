// login.js

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('loginForm');
    const telegramCheckbox = document.getElementById('telegramMode');
    const telegramIdGroup = document.getElementById('telegramIdGroup');
    let failedAttempts = parseInt(localStorage.getItem('failedAttempts') || '0');
    const blockedUntil = localStorage.getItem('blockedUntil');

    // Если есть блокировка
    if (blockedUntil && Date.now() < parseInt(blockedUntil)) {
        const remaining = Math.ceil((parseInt(blockedUntil) - Date.now()) / 1000 / 60);
        showToast('Доступ заблокирован на ' + remaining + ' минут', 'error');
        document.querySelector('button[type="submit"]').disabled = true;
    }

    // Показать/скрыть поле Telegram ID
    telegramCheckbox.addEventListener('change', function(e) {
        telegramIdGroup.classList.toggle('hidden', !e.target.checked);
    });

    // Отправка формы
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Проверка блокировки
        if (blockedUntil && Date.now() < parseInt(blockedUntil)) {
            showToast('Вход временно заблокирован', 'error');
            return;
        }

        const login = document.getElementById('login').value;
        const password = document.getElementById('password').value;
        const useTelegram = telegramCheckbox.checked;
        const telegramId = useTelegram ? document.getElementById('telegramId').value : null;

        // ─── Telegram-вход ──────────────────────────────────────
        if (useTelegram && telegramId) {
            try {
                const resp = await fetch('/api/auth/login/tg', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tg_uuid: telegramId })
                });
                const data = await resp.json();
                if (!resp.ok || !data.success) {
                    showToast(data.detail || data.error || 'Ошибка входа через Telegram', 'error');
                    return;
                }
                saveToken(data.token);
                saveRole(data.role);
                localStorage.removeItem('failedAttempts');
                localStorage.removeItem('blockedUntil');
                window.location.href = '/main/';
            } catch (err) {
                showToast('Ошибка соединения с сервером', 'error');
            }
            return;
        }

        // ─── Обычный вход ───────────────────────────────────────
        try {
            const resp = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ login, password })
            });
            const data = await resp.json();

            if (!resp.ok || !data.success) {
                failedAttempts++;
                localStorage.setItem('failedAttempts', failedAttempts);

                if (failedAttempts >= 5) {
                    const blockUntil = Date.now() + 15 * 60 * 1000;
                    localStorage.setItem('blockedUntil', blockUntil);
                    showToast('Превышено количество попыток. Блокировка 15 минут', 'error');
                    document.querySelector('button[type="submit"]').disabled = true;
                } else {
                    const remaining = 5 - failedAttempts;
                    showToast('Неверный логин или пароль. Осталось попыток: ' + remaining, 'error');
                }
                return;
            }

            // Успешный вход
            saveToken(data.token);
            saveRole(data.role);
            localStorage.removeItem('failedAttempts');
            localStorage.removeItem('blockedUntil');
            window.location.href = '/main/';

        } catch (err) {
            showToast('Ошибка соединения с сервером', 'error');
        }
    });
});
