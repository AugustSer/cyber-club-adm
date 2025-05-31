import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
import sys
import os
import subprocess
from datetime import datetime
import json


class ComputerClubClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Компьютерный клуб - Клиентский доступ")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Настройки подключения к серверу
        self.load_config()

        # Переменные состояния
        self.access_granted = False
        self.check_thread = None
        self.running = True

        self.create_widgets()
        self.center_window()

        # Запускаем проверку времени сервера
        self.sync_time()

    def load_config(self):
        """Загружает конфигурацию из файла или использует значения по умолчанию"""
        try:
            # Пробуем загрузить из JSON файла
            if os.path.exists('client_settings.json'):
                with open('client_settings.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    server_host = config.get('server_host', '192.168.1.100')
                    server_port = config.get('server_port', 5000)
                    self.server_url = f"http://{server_host}:{server_port}"
                    self.log_message(f"Конфигурация загружена из файла: {self.server_url}")
                    return
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")

        # Используем значения по умолчанию или переменные среды
        server_host = os.environ.get('SERVER_HOST', '192.168.0.111')  # IP вашего ноутбука
        server_port = os.environ.get('SERVER_PORT', '5000')
        self.server_url = f"http://{server_host}:{server_port}"

    def log_message(self, message):
        """Добавляет сообщение в лог"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
        else:
            # Если лог еще не создан, выводим в консоль
            print(log_entry.strip())

    def center_window(self):
        """Центрирует окно на экране"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f'+{x}+{y}')

    def create_widgets(self):
        """Создает интерфейс приложения"""
        # Главная рамка
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = ttk.Label(main_frame, text="Система доступа к компьютеру",
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))

        # Информация о времени
        self.time_frame = ttk.LabelFrame(main_frame, text="Информация о времени", padding="10")
        self.time_frame.pack(fill=tk.X, pady=(0, 20))

        self.local_time_label = ttk.Label(self.time_frame, text="Локальное время: --:--:--")
        self.local_time_label.pack(anchor=tk.W)

        self.server_time_label = ttk.Label(self.time_frame, text="Время сервера: --:--:--")
        self.server_time_label.pack(anchor=tk.W)

        # Форма ввода кода доступа
        access_frame = ttk.LabelFrame(main_frame, text="Введите код доступа", padding="10")
        access_frame.pack(fill=tk.X, pady=(0, 20))

        self.access_code_var = tk.StringVar()
        self.access_code_entry = ttk.Entry(access_frame, textvariable=self.access_code_var,
                                           font=('Arial', 14), width=20)
        self.access_code_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.access_code_entry.bind('<Return>', lambda e: self.check_access())

        self.check_button = ttk.Button(access_frame, text="Проверить доступ",
                                       command=self.check_access)
        self.check_button.pack(side=tk.LEFT)

        # Статус доступа
        self.status_frame = ttk.LabelFrame(main_frame, text="Статус доступа", padding="10")
        self.status_frame.pack(fill=tk.X, pady=(0, 20))

        self.status_label = ttk.Label(self.status_frame, text="Доступ не предоставлен",
                                      font=('Arial', 12), foreground='red')
        self.status_label.pack()

        self.details_label = ttk.Label(self.status_frame, text="",
                                       font=('Arial', 10), foreground='gray')
        self.details_label.pack()

        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.lock_button = ttk.Button(button_frame, text="Заблокировать компьютер",
                                      command=self.lock_computer, state=tk.DISABLED)
        self.lock_button.pack(side=tk.LEFT, padx=(0, 10))

        self.refresh_button = ttk.Button(button_frame, text="Обновить статус",
                                         command=self.refresh_status)
        self.refresh_button.pack(side=tk.LEFT)

        # Лог активности
        log_frame = ttk.LabelFrame(main_frame, text="Лог активности", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=8, width=50, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Запускаем обновление времени
        self.update_time()

        # Фокус на поле ввода
        self.access_code_entry.focus()

    def sync_time(self):
        """Синхронизирует время с сервером"""
        try:
            response = requests.get(f"{self.server_url}/api/server_time", timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.log_message(f"Синхронизация с сервером успешна. Время сервера: {data['server_time']}")
                return True
        except requests.exceptions.ConnectTimeout:
            self.log_message("Таймаут подключения к серверу")
            messagebox.showerror("Ошибка сети",
                                 f"Таймаут подключения к серверу:\n{self.server_url}\n\n"
                                 "Возможные причины:\n"
                                 "• Устройства в разных сетях\n"
                                 "• Сервер не запущен\n"
                                 "• Брандмауэр блокирует соединение")
            return False
        except requests.exceptions.ConnectionError:
            self.log_message("Ошибка соединения с сервером")
            messagebox.showerror("Ошибка сети",
                                 f"Не удается подключиться к серверу:\n{self.server_url}\n\n"
                                 "Проверьте:\n"
                                 "• IP-адрес сервера правильный\n"
                                 "• Сервер запущен и доступен\n"
                                 "• Настройки сети виртуальной машины")
            return False
        except requests.exceptions.RequestException as e:
            self.log_message(f"Ошибка подключения к серверу: {str(e)}")
            messagebox.showwarning("Ошибка подключения",
                                   f"Ошибка подключения к серверу:\n{self.server_url}\n\nОшибка: {str(e)}")
            return False

    def update_time(self):
        """Обновляет отображение времени"""
        if not self.running:
            return

        # Обновляем локальное время
        local_time = datetime.now().strftime('%H:%M:%S')
        self.local_time_label.config(text=f"Локальное время: {local_time}")

        # Периодически обновляем время сервера
        if hasattr(self, '_last_server_sync'):
            if time.time() - self._last_server_sync > 30:  # Обновляем каждые 30 секунд
                self.update_server_time()
        else:
            self.update_server_time()

        # Планируем следующее обновление
        self.root.after(1000, self.update_time)

    def update_server_time(self):
        """Обновляет время сервера"""
        try:
            response = requests.get(f"{self.server_url}/api/server_time", timeout=3)
            if response.status_code == 200:
                data = response.json()
                self.server_time_label.config(text=f"Время сервера: {data['server_time']}")
                self._last_server_sync = time.time()
        except requests.exceptions.RequestException:
            self.server_time_label.config(text="Время сервера: Нет подключения")

    def check_access(self):
        """Проверяет код доступа"""
        access_code = self.access_code_var.get().strip().upper()

        if not access_code:
            messagebox.showwarning("Ошибка", "Введите код доступа")
            return

        self.log_message(f"Проверка кода доступа: {access_code}")

        try:
            response = requests.get(f"{self.server_url}/api/check_access/{access_code}", timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data['access_granted']:
                    self.grant_access(data)
                else:
                    self.deny_access(data['message'])
            else:
                self.deny_access("Ошибка сервера")

        except requests.exceptions.RequestException as e:
            self.log_message(f"Ошибка при проверке доступа: {str(e)}")
            messagebox.showerror("Ошибка сети",
                                 "Не удается проверить код доступа. Проверьте подключение к сети.")

    def grant_access(self, data):
        """Предоставляет доступ к компьютеру"""
        self.access_granted = True
        self.status_label.config(text="✅ ДОСТУП РАЗРЕШЕН", foreground='green')

        details = f"Пользователь: {data['user']}\n"
        details += f"Компьютер: {data['computer']}\n"
        details += f"Окончание брони: {data['end_time']}"
        self.details_label.config(text=details)

        self.lock_button.config(state=tk.NORMAL)
        self.access_code_entry.config(state=tk.DISABLED)
        self.check_button.config(state=tk.DISABLED)

        self.log_message(f"Доступ предоставлен пользователю {data['user']}")

        # Запускаем мониторинг сессии
        self.start_session_monitoring(data['end_time'])

        messagebox.showinfo("Доступ разрешен",
                            f"Добро пожаловать, {data['user']}!\n\nВремя окончания сессии: {data['end_time']}")

    def deny_access(self, message):
        """Отклоняет доступ"""
        self.access_granted = False
        self.status_label.config(text="❌ ДОСТУП ЗАПРЕЩЕН", foreground='red')
        self.details_label.config(text=message)

        self.lock_button.config(state=tk.DISABLED)

        self.log_message(f"Доступ запрещен: {message}")
        messagebox.showerror("Доступ запрещен", message)

    def start_session_monitoring(self, end_time_str):
        """Запускает мониторинг сессии"""

        def monitor():
            try:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')

                while self.running and self.access_granted:
                    current_time = datetime.now()

                    if current_time >= end_time:
                        self.root.after(0, self.session_expired)
                        break

                    time.sleep(60)  # Проверяем каждую минуту

            except Exception as e:
                self.log_message(f"Ошибка мониторинга сессии: {str(e)}")

        if self.check_thread and self.check_thread.is_alive():
            return

        self.check_thread = threading.Thread(target=monitor, daemon=True)
        self.check_thread.start()

    def session_expired(self):
        """Обработка истечения времени сессии"""
        self.access_granted = False
        self.status_label.config(text="⏰ ВРЕМЯ СЕССИИ ИСТЕКЛО", foreground='orange')
        self.details_label.config(text="Время брони закончилось")

        self.lock_button.config(state=tk.DISABLED)
        self.access_code_entry.config(state=tk.NORMAL)
        self.check_button.config(state=tk.NORMAL)
        self.access_code_var.set("")

        self.log_message("Время сессии истекло")
        messagebox.showwarning("Время истекло",
                               "Время вашей сессии истекло. Компьютер будет заблокирован.")

        # Автоматически блокируем компьютер
        self.lock_computer()

    def lock_computer(self):
        """Блокирует компьютер"""
        try:
            # В Windows используем команду rundll32 для блокировки
            os.system("rundll32.exe user32.dll,LockWorkStation")
            self.log_message("Компьютер заблокирован")
        except Exception as e:
            self.log_message(f"Ошибка при блокировке компьютера: {str(e)}")

    def refresh_status(self):
        """Обновляет статус подключения"""
        self.log_message("Обновление статуса...")
        if self.sync_time():
            self.log_message("Соединение с сервером активно")
        else:
            self.log_message("Нет соединения с сервером")

    def on_closing(self):
        """Обработка закрытия приложения"""
        self.running = False
        if self.check_thread and self.check_thread.is_alive():
            self.check_thread.join(timeout=1)
        self.root.destroy()

    def run(self):
        """Запускает приложение"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_message("Клиентское приложение запущено")
        self.log_message(f"Подключение к серверу: {self.server_url}")
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = ComputerClubClient()
        app.run()
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Ошибка запуска приложения:\n{str(e)}")
        sys.exit(1)
