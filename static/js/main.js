// Основной JavaScript файл для кибер-клуба

// Глобальные переменные
let currentUser = null;
let bookingsData = [];
let computersData = [];
let customersData = [];

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Основная функция инициализации
function initializeApp() {
    console.log('Initializing Cyber Club Management System...');

    // Инициализация Bootstrap компонентов
    initializeBootstrapComponents();

    // Загрузка данных
    loadInitialData();

    // Настройка обработчиков событий
    setupEventListeners();

    // Инициализация форм
    initializeForms();
}

// Инициализация Bootstrap компонентов
function initializeBootstrapComponents() {
    // Инициализация всех tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Инициализация всех popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Загрузка начальных данных
function loadInitialData() {
    // Проверяем, на какой странице мы находимся
    const currentPage = getCurrentPage();

    switch(currentPage) {
        case 'index':
            loadDashboardData();
            break;
        case 'bookings':
            // Данные загружаются на странице бронирований
            break;
        case 'reports':
            // Данные загружаются на странице отчетов
            break;
    }
}

// Определение текущей страницы
function getCurrentPage() {
    const path = window.location.pathname;
    if (path === '/' || path === '/index') return 'index';
    if (path.includes('bookings')) return 'bookings';
    if (path.includes('reports')) return 'reports';
    return 'unknown';
}

// Загрузка данных для дашборда
function loadDashboardData() {
    Promise.all([
        fetchData('/api/bookings'),
        fetchData('/api/computers'),
        fetchData('/api/customers')
    ])
    .then(([bookings, computers, customers]) => {
        bookingsData = bookings;
        computersData = computers;
        customersData = customers;

        updateDashboardStats();
    })
    .catch(error => {
        console.error('Error loading dashboard data:', error);
        showNotification('Ошибка загрузки данных', 'error');
    });
}

// Обновление статистики на дашборде
function updateDashboardStats() {
    // Активные бронирования
    const activeBookings = bookingsData.filter(b => b.status === 'active').length;
    updateElement('active-bookings', activeBookings);

    // Доход за сегодня
    const today = new Date().toISOString().split('T')[0];
    const todayBookings = bookingsData.filter(b =>
        b.start_time.startsWith(today) && b.status !== 'cancelled'
    );
    const todayRevenue = todayBookings.reduce((sum, booking) => sum + (booking.total_cost || 0), 0);
    updateElement('today-revenue', `${todayRevenue.toFixed(2)} ₽`);

    // Свободные компьютеры
    const availableComputers = computersData.filter(c => c.status === 'available').length;
    updateElement('available-computers', availableComputers);

    // Всего клиентов
    updateElement('total-customers', customersData.length);
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Обработка кликов по кнопкам экспорта
    document.addEventListener('click', function(e) {
        if (e.target.matches('.export-btn, .export-btn *')) {
            const btn = e.target.closest('.export-btn');
            if (btn) {
                const format = btn.dataset.format;
                const reportId = btn.dataset.reportId;
                if (format && reportId) {
                    exportReport(reportId, format);
                }
            }
        }
    });

    // Обработка изменений в формах
    document.addEventListener('change', function(e) {
        if (e.target.matches('.auto-calculate')) {
            calculateBookingCost();
        }
    });

    // Обработка submit форм
    document.addEventListener('submit', function(e) {
        if (e.target.matches('.ajax-form')) {
            e.preventDefault();
            handleFormSubmit(e.target);
        }
    });
}

// Инициализация форм
function initializeForms() {
    // Установка значений по умолчанию для дат
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];

    dateInputs.forEach(input => {
        if (!input.value) {
            input.value = today;
        }
    });

    // Установка значений по умолчанию для datetime-local
    const datetimeInputs = document.querySelectorAll('input[type="datetime-local"]');
    const now = new Date();
    const defaultStart = new Date(now.getTime() + 60 * 60 * 1000); // +1 час
    const defaultEnd = new Date(defaultStart.getTime() + 2 * 60 * 60 * 1000); // +2 часа

    datetimeInputs.forEach((input, index) => {
        if (!input.value) {
            if (index % 2 === 0) { // Четные - время начала
                input.value = defaultStart.toISOString().slice(0, 16);
            } else { // Нечетные - время окончания
                input.value = defaultEnd.toISOString().slice(0, 16);
            }
        }
    });
}

// Универсальная функция для выполнения HTTP запросов
async function fetchData(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`Error fetching data from ${url}:`, error);
        throw error;
    }
}

// Функция для безопасного обновления элементов
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

// Функция показа уведомлений
function showNotification(message, type = 'info', duration = 5000) {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';

    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; max-width: 500px;';
    alert.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${getIconForType(type)} me-2"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alert);

    // Автоматическое удаление
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, duration);

    return alert;
}

// Получение иконки для типа уведомления
function getIconForType(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Функция обработки отправки форм
async function handleFormSubmit(form) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    const url = form.action || form.dataset.action;
    const method = form.method || 'POST';

    try {
        const response = await fetchData(url, {
            method: method,
            body: JSON.stringify(data)
        });

        if (response.success) {
            showNotification('Операция выполнена успешно!', 'success');

            // Закрытие модального окна если есть
            const modal = form.closest('.modal');
            if (modal) {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            }

            // Перезагрузка страницы или обновление данных
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showNotification(response.message || 'Ошибка при выполнении операции', 'error');
        }
    } catch (error) {
        console.error('Form submission error:', error);
        showNotification('Ошибка при отправке данных', 'error');
    }
}

// Функция для валидации форм
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Функция форматирования дат
function formatDate(dateString, options = {}) {
    const date = new Date(dateString);
    const defaultOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    };

    return date.toLocaleDateString('ru-RU', { ...defaultOptions, ...options });
}

// Функция форматирования валюты
function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB'
    }).format(amount);
}

// Функция для работы с Local Storage
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Error saving to localStorage:', error);
        }
    },

    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return defaultValue;
        }
    },

    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('Error removing from localStorage:', error);
        }
    },

    clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('Error clearing localStorage:', error);
        }
    }
};

// Функция для дебаунсинга
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Функция для троттлинга
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Экспорт функций для использования в других файлах
window.CyberClub = {
    showNotification,
    fetchData,
    updateElement,
    formatDate,
    formatCurrency,
    Storage,
    debounce,
    throttle
};

// Логирование успешной инициализации
console.log('Cyber Club Management System initialized successfully!');
