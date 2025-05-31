// Главный JavaScript файл для компьютерного клуба

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Инициализация всех компонентов
    initAutoRefresh();
    initAnimations();
    initFormValidation();
    initTooltips();

    console.log('Computer Club Management System initialized');
}

// Автообновление статуса компьютеров
function initAutoRefresh() {
    if (window.location.pathname.includes('/admin/computers') || window.location.pathname === '/admin') {
        updateComputerStatus();
        setInterval(updateComputerStatus, 30000); // Обновление каждые 30 секунд
    }
}

async function updateComputerStatus() {
    try {
        const response = await fetch('/api/computers/status');
        const computers = await response.json();

        // Обновление статуса на странице компьютеров
        computers.forEach(computer => {
            updateComputerCard(computer);
        });

        // Обновление дашборда
        updateDashboardStats(computers);

    } catch (error) {
        console.error('Ошибка обновления статуса:', error);
    }
}

function updateComputerCard(computer) {
    const card = document.querySelector(`[data-computer-id="${computer.id}"]`);
    if (!card) return;

    // Обновление статуса
    const statusBadge = card.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.className = `status-badge status-${computer.status}`;
        statusBadge.textContent = getStatusText(computer.status);
    }

    // Обновление информации о текущем клиенте
    const clientInfo = card.querySelector('.current-client');
    if (clientInfo) {
        if (computer.current_client) {
            clientInfo.textContent = `Клиент: ${computer.current_client}`;
            clientInfo.style.display = 'block';
        } else {
            clientInfo.style.display = 'none';
        }
    }

    // Обновление времени сессии
    const sessionTime = card.querySelector('.session-time');
    if (sessionTime && computer.session_duration > 0) {
        sessionTime.textContent = `Время: ${computer.session_duration.toFixed(2)} ч.`;
        sessionTime.style.display = 'block';
    } else if (sessionTime) {
        sessionTime.style.display = 'none';
    }

    // Обновление стоимости
    const currentCost = card.querySelector('.current-cost');
    if (currentCost && computer.current_cost > 0) {
        currentCost.textContent = `Сумма: ${computer.current_cost.toFixed(2)} ₽`;
        currentCost.style.display = 'block';
    } else if (currentCost) {
        currentCost.style.display = 'none';
    }
}

function updateDashboardStats(computers) {
    const occupied = computers.filter(c => c.status === 'occupied').length;
    const available = computers.filter(c => c.status === 'available').length;

    // Обновление счетчиков на дашборде
    const occupiedElement = document.getElementById('occupied-count');
    const availableElement = document.getElementById('available-count');

    if (occupiedElement) {
        animateNumber(occupiedElement, occupied);
    }

    if (availableElement) {
        animateNumber(availableElement, available);
    }
}

function getStatusText(status) {
    const statusMap = {
        'available': 'Свободен',
        'occupied': 'Занят',
        'maintenance': 'Обслуживание'
    };
    return statusMap[status] || status;
}

// Анимации
function initAnimations() {
    // Анимация появления карточек
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Наблюдение за карточками
    document.querySelectorAll('.card-custom, .stats-card').forEach(card => {
        observer.observe(card);
    });
}

function animateNumber(element, targetNumber) {
    const currentNumber = parseInt(element.textContent) || 0;
    const increment = targetNumber > currentNumber ? 1 : -1;

    if (currentNumber === targetNumber) return;

    const timer = setInterval(() => {
        const current = parseInt(element.textContent) || 0;
        const next = current + increment;

        element.textContent = next;

        if (next === targetNumber) {
            clearInterval(timer);
        }
    }, 50);
}

// Валидация форм
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'Это поле обязательно для заполнения');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });

    return isValid;
}

function showFieldError(field, message) {
    clearFieldError(field);

    field.classList.add('is-invalid');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;

    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

// Инициализация всплывающих подсказок
function initTooltips() {
    // Использование Bootstrap tooltips если они доступны
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

// Утилитарные функции
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB'
    }).format(amount);
}

function formatDuration(hours) {
    const h = Math.floor(hours);
    const m = Math.floor((hours - h) * 60);
    return `${h}ч ${m}м`;
}

// Обработчики событий для кнопок
document.addEventListener('click', function(e) {
    // Кнопка запуска сессии
    if (e.target.matches('.btn-start-session')) {
        handleStartSession(e);
    }

    // Кнопка остановки сессии
    if (e.target.matches('.btn-stop-session')) {
        handleStopSession(e);
    }

    // Кнопка создания бронирования
    if (e.target.matches('.btn-create-booking')) {
        window.location.href = '/admin/bookings/create';
    }
});

function handleStartSession(e) {
    const computerId = e.target.dataset.computerId;
    const computerName = e.target.dataset.computerName;

    const clientName = prompt(`Запуск сессии на ${computerName}\nВведите имя клиента:`);

    if (clientName && clientName.trim()) {
        // Отправка формы
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/computers/${computerId}/start`;

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'client_name';
        input.value = clientName.trim();

        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }
}

function handleStopSession(e) {
    const computerId = e.target.dataset.computerId;
    const computerName = e.target.dataset.computerName;

    if (confirm(`Завершить сессию на ${computerName}?`)) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/computers/${computerId}/stop`;

        document.body.appendChild(form);
        form.submit();
    }
}

// Функции для работы с местным временем
function updateClocks() {
    const clocks = document.querySelectorAll('.live-clock');
    clocks.forEach(clock => {
        clock.textContent = new Date().toLocaleTimeString('ru-RU');
    });
}

// Обновление часов каждую секунду
setInterval(updateClocks, 1000);
updateClocks();

// Экспорт для использования в других скриптах
window.ComputerClub = {
    updateComputerStatus,
    showNotification,
    formatCurrency,
    formatDuration
};
