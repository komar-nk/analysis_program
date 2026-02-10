// ==============================
// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И ФУНКЦИИ
// ==============================

let currentUser = JSON.parse(localStorage.getItem('currentUser')) || null;
let users = JSON.parse(localStorage.getItem('cosmosUsers')) || [];
let savedTerritories = JSON.parse(localStorage.getItem('cosmosTerritories')) || [];
let monitoringData = JSON.parse(localStorage.getItem('cosmosMonitoring')) || [];
async function autoSyncAuth() {
    if (!currentUser) {
        console.log('Нет пользователя для синхронизации');
        return false;
    }

    console.log('🔄 Автосинхронизация авторизации...');

    try {
        // 1. Пробуем синхронизировать
        const response = await fetch('/api/auth/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include', // ВАЖНО!
            body: JSON.stringify({
                username: currentUser.username,
                login: currentUser.login,
                force: true
            })
        });

        // 2. Если ответ не OK, пробуем регистрацию
        if (!response.ok) {
            console.log('Синхронизация не удалась, пробуем регистрацию...');

            const registerResponse = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    username: currentUser.username,
                    password: 'auto_' + Date.now().toString().slice(-6)
                })
            });

            const registerData = await registerResponse.json();
            console.log('Регистрация на сервере:', registerData);

            return registerData.success;
        }

        const data = await response.json();
        console.log(' Синхронизация успешна:', data);
        return data.success;

    } catch (error) {
        console.log('⚠ Сервер недоступен, работаем офлайн');
        return false; // Офлайн режим
    }
}



function initPage() {
    console.log('Инициализация страницы...');

    // Проверяем авторизацию
    if (!currentUser && window.location.pathname.includes('cabinet.html')) {
        window.location.href = 'index.html';
        return;
    }

    if (document.getElementById('stars')) {
        createStars();
    }

    initMenu();
    initAuth();
    updateUserInfo();

    if (currentUser) {
        setTimeout(() => {
            autoSyncAuth().then(success => {
                if (success) {
                    console.log(' Авторизация готова к работе!');
                }
            });
        }, 500);
    }

    // Вызываем специфичную инициализацию для каждой страницы
    if (typeof pageSpecificInit === 'function') {
        pageSpecificInit();
    }
}

// Создание звездного фона
function createStars() {
    const container = document.getElementById('stars');
    if (!container) return;

    container.innerHTML = '';
    const count = 150;

    for (let i = 0; i < count; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        const size = Math.random() * 3 + 1;
        star.style.width = size + 'px';
        star.style.height = size + 'px';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.opacity = Math.random() * 0.5 + 0.3;
        star.style.animationDelay = Math.random() * 3 + 's';
        star.style.animationDuration = (Math.random() * 2 + 1) + 's';
        container.appendChild(star);
    }
}

// Инициализация меню
function initMenu() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileMenuBtn && navMenu) {
        mobileMenuBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            navMenu.classList.toggle('active');
        });

        // Закрытие меню при клике на ссылку
        const navLinks = navMenu.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navMenu.classList.remove('active');
            });
        });

        // Закрытие меню при клике вне его
        document.addEventListener('click', function(e) {
            if (!navMenu.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                navMenu.classList.remove('active');
            }
        });
    }
}

// Инициализация авторизации
function initAuth() {
    const authBtn = document.getElementById('authBtn');
    const authModal = document.getElementById('authModal');
    const closeAuth = document.getElementById('closeAuth');
    const switchToRegister = document.getElementById('switchToRegister');
    const switchToLogin = document.getElementById('switchToLogin');


    if (!authBtn || !authModal) return;

    // Проверяем авторизацию при загрузке
    if (currentUser) {
        authBtn.style.display = 'none';
    }

    // Открытие модального окна
    authBtn.addEventListener('click', function(e) {
        e.preventDefault();
        authModal.classList.add('active');
    });

    // Закрытие модального окна
    if (closeAuth) {
        closeAuth.addEventListener('click', function(e) {
            e.preventDefault();
            authModal.classList.remove('active');
        });
    }

    // Клик по фону для закрытия
    authModal.addEventListener('click', function(e) {
        if (e.target === authModal) {
            authModal.classList.remove('active');
        }
    });

    // Переключение между формами
    if (switchToRegister) {
        switchToRegister.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('registerForm').style.display = 'block';
        });
    }

    if (switchToLogin) {
        switchToLogin.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('registerForm').style.display = 'none';
            document.getElementById('loginForm').style.display = 'block';
        });
    }

    // Обработка формы входа
    const loginForm = document.getElementById('loginFormElement');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value;

            if (!username || !password) {
                showNotification('Заполните все поля', 'error');
                return;
            }

            // Проверка пользователя
            const user = users.find(u => u.username === username && u.password === password);
            if (user) {
                currentUser = { username: user.username, login: user.username };
                localStorage.setItem('currentUser', JSON.stringify(currentUser));

                showNotification('Вход выполнен успешно!', 'success');
                authModal.classList.remove('active');

                // Обновляем информацию о пользователе
                updateUserInfo();

                // Перезагружаем страницу
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showNotification('Неверный логин или пароль', 'error');
            }
        });
    }

    // Обработка формы регистрации
    const registerForm = document.getElementById('registerFormElement');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('registerUsername').value.trim();
            const password = document.getElementById('registerPassword').value;
            const passwordConfirm = document.getElementById('registerPasswordConfirm').value;

            // Проверки
            if (!username || !password) {
                showNotification('Заполните все поля', 'error');
                return;
            }

            if (password.length < 3) {
                showNotification('Пароль должен быть не менее 3 символов', 'error');
                return;
            }

            if (password !== passwordConfirm) {
                showNotification('Пароли не совпадают', 'error');
                return;
            }

            if (users.some(u => u.username === username)) {
                showNotification('Пользователь с таким логином уже существует', 'error');
                return;
            }

            // Создание нового пользователя
            const newUser = {
                username: username,
                password: password,
                createdAt: new Date().toISOString(),
                notificationEmails: []
            };

            users.push(newUser);
            localStorage.setItem('cosmosUsers', JSON.stringify(users));

            currentUser = { username: username, login: username };
            localStorage.setItem('currentUser', JSON.stringify(currentUser));

            showNotification('Регистрация успешна!', 'success');
            authModal.classList.remove('active');

            // Обновляем информацию о пользователе
            updateUserInfo();

            // Перезагружаем страницу
            setTimeout(() => {
                location.reload();
            }, 1000);
        });
    }
}

// Обновление информации о пользователе в шапке
function updateUserInfo() {
    const userInfo = document.getElementById('userInfo');
    const authBtn = document.getElementById('authBtn');

    if (userInfo && authBtn) {
        if (currentUser) {
            userInfo.textContent = `Привет, ${currentUser.username}`;
            authBtn.style.display = 'none';
        } else {
            userInfo.textContent = '';
            authBtn.style.display = 'block';
        }
    }
}

// Показ уведомлений
function showNotification(message, type = 'info') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button class="notification-close">&times;</button>
    `;

    // Стили для уведомления
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        background: type === 'success' ? '#10b981' : type === 'error' ? '#ff4444' : '#4a9eff',
        color: 'white',
        borderRadius: '8px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        zIndex: '10000',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        animation: 'slideIn 0.3s ease'
    });

    // Стиль для кнопки закрытия
    const closeBtn = notification.querySelector('.notification-close');
    Object.assign(closeBtn.style, {
        background: 'transparent',
        border: 'none',
        color: 'white',
        fontSize: '1.2rem',
        cursor: 'pointer',
        padding: '0',
        marginLeft: '10px'
    });

    document.body.appendChild(notification);

    // Закрытие уведомления
    closeBtn.addEventListener('click', function() {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    });

    // Автоматическое закрытие через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, 5000);
}

// Функции для работы с email уведомлениями
function addNotificationEmailToUser(email) {
    const userIndex = users.findIndex(u => u.username === currentUser.username);

    if (userIndex === -1) return { success: false, message: 'Пользователь не найден' };

    // Инициализируем массив если его нет
    if (!users[userIndex].notificationEmails) {
        users[userIndex].notificationEmails = [];
    }

    // Проверяем, есть ли уже такой email
    if (users[userIndex].notificationEmails.some(e => e.address.toLowerCase() === email.toLowerCase())) {
        return { success: false, message: 'Этот email уже добавлен' };
    }

    // Простая валидация email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return { success: false, message: 'Введите корректный email' };
    }

    // Определяем, будет ли этот email основным
    const isFirstEmail = users[userIndex].notificationEmails.length === 0;

    // Добавляем email
    users[userIndex].notificationEmails.push({
        address: email,
        addedAt: new Date().toISOString(),
        isPrimary: isFirstEmail,
        verified: false
    });

    // Сохраняем в локальное хранилище
    localStorage.setItem('cosmosUsers', JSON.stringify(users));

    // Сохраняем в базу данных через API
    saveEmailToServer(email, isFirstEmail);

    return { success: true, message: 'Email успешно добавлен' + (isFirstEmail ? ' (основной)' : ''), isFirst: isFirstEmail };
}

// Новая функция для сохранения email на сервере
async function saveEmailToServer(email, isPrimary) {
    try {
        const response = await fetch('/api/user/save-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                email: email,
                isPrimary: isPrimary,
                username: currentUser.username
            })
        });

        const data = await response.json();
        console.log('Email сохранен на сервере:', data);
    } catch (error) {
        console.error('Ошибка сохранения email на сервере:', error);
    }
}

function removeNotificationEmailFromUser(emailIndex) {
    const userIndex = users.findIndex(u => u.username === currentUser.username);

    if (userIndex === -1) return { success: false, message: 'Пользователь не найден' };

    if (!users[userIndex].notificationEmails || emailIndex >= users[userIndex].notificationEmails.length) {
        return { success: false, message: 'Email не найден' };
    }

    const email = users[userIndex].notificationEmails[emailIndex];
    const isPrimary = email.isPrimary;

    // Если удаляем основной email и есть другие email
    if (isPrimary && users[userIndex].notificationEmails.length > 1) {
        const nextIndex = emailIndex === 0 ? 1 : 0;
        users[userIndex].notificationEmails[nextIndex].isPrimary = true;
    }

    // Удаляем email
    users[userIndex].notificationEmails.splice(emailIndex, 1);

    // Сохраняем изменения
    localStorage.setItem('cosmosUsers', JSON.stringify(users));

    // Обновляем текущего пользователя
    currentUser.notificationEmails = users[userIndex].notificationEmails;
    localStorage.setItem('currentUser', JSON.stringify(currentUser));

    return { success: true, message: 'Email удален' + (isPrimary ? ' (был основной)' : '') };
}

function makePrimaryEmailForUser(emailIndex) {
    const userIndex = users.findIndex(u => u.username === currentUser.username);

    if (userIndex === -1) return { success: false, message: 'Пользователь не найден' };

    if (!users[userIndex].notificationEmails || emailIndex >= users[userIndex].notificationEmails.length) {
        return { success: false, message: 'Email не найден' };
    }

    // Сбрасываем все флаги isPrimary
    users[userIndex].notificationEmails.forEach(email => {
        email.isPrimary = false;
    });

    // Устанавливаем выбранный как основной
    users[userIndex].notificationEmails[emailIndex].isPrimary = true;

    // Сохраняем изменения
    localStorage.setItem('cosmosUsers', JSON.stringify(users));

    // Обновляем текущего пользователя
    currentUser.notificationEmails = users[userIndex].notificationEmails;
    localStorage.setItem('currentUser', JSON.stringify(currentUser));

    return { success: true, message: 'Основной email изменен' };
}


// Инициализация при полной загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM загружен, инициализируем страницу...');
    initPage();
});
// Функции для работы с датами
function formatDate(date) {
    if (!date) return '—';
    return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}

function formatDateTime(date) {
    if (!date) return '—';
    return date.toLocaleDateString('ru-RU') + ' ' +
           date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function formatDateForFilename(date) {
    if (!date) return 'unknown';
    return date.toISOString().slice(0, 10).replace(/-/g, '');
}
function showComparisonDetails() {
    // Здесь можно показать детальный отчет
    alert('Детальный анализ изменений пока недоступен.\nРезультаты анализа сохранены на сервере.');
}
async function apiFetch(url, options = {}) {
    // Базовая конфигурация
    const defaultOptions = {
        credentials: 'include', // ОБЯЗАТЕЛЬНО для куки и сессии
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };

    // Объединяем опции
    const mergedOptions = { ...defaultOptions, ...options };

    console.log(' API запрос:', {
        url: url,
        method: mergedOptions.method || 'GET',
        body: mergedOptions.body ? JSON.parse(mergedOptions.body) : undefined
    });

    try {
        const startTime = Date.now();
        const response = await fetch(url, mergedOptions);
        const endTime = Date.now();

        console.log(`📡 API ответ (${endTime - startTime}ms):`, {
            url: url,
            status: response.status,
            statusText: response.statusText,
            headers: Object.fromEntries(response.headers.entries())
        });

        // Проверяем авторизацию
        if (response.status === 401 || response.status === 403) {
            console.warn(' Ошибка авторизации при запросе к:', url);

            // Пробуем синхронизировать авторизацию
            if (currentUser) {
                console.log(' Пробуем синхронизировать авторизацию...');
                await syncAuthWithServer(currentUser.username);

                // Повторяем запрос
                console.log(' Повторяем запрос...');
                return await fetch(url, mergedOptions);
            }

            throw new Error('Unauthorized');
        }

        // Проверяем другие ошибки
        if (!response.ok && response.status !== 404) {
            const errorText = await response.text();
            console.error(' Ошибка HTTP:', {
                status: response.status,
                statusText: response.statusText,
                error: errorText
            });

            // Пробуем распарсить как JSON
            try {
                const errorJson = JSON.parse(errorText);
                throw new Error(errorJson.message || errorText);
            } catch {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        }

        return response;
    } catch (error) {
        console.error(' Сетевая ошибка при запросе к', url, ':', error);

        // Проверяем подключение к серверу
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            showNotification('Нет подключения к серверу. Проверьте, запущен ли Flask.', 'error');
        }

        throw error;
    }
}