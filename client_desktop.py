import webbrowser
import subprocess
import threading
import time
import client_terminal  # ваш Flask-приложение

def run_flask():
    client_terminal.client_app.run(host='127.0.0.1', port=5001)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    time.sleep(1)  # Ждем запуска сервера

    # Путь к Chrome (пример для Windows)
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    # Запуск Chrome в полноэкранном киоск-режиме
    subprocess.Popen([chrome_path, "--kiosk", "http://127.0.0.1:5001/"])

    # Если хотите просто открыть браузер без киоска:
    # webbrowser.open("http://127.0.0.1:5001/")

    # Просто держим скрипт живым
    flask_thread.join()
