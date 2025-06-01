from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os

client_app = Flask(__name__, template_folder='templates/client')
client_app.secret_key = os.environ.get("CLIENT_SECRET", "client-secret-key")

ADMIN_SERVER_URL = os.environ.get("ADMIN_SERVER_URL", "http://localhost:5000")

@client_app.route('/')
def client_index():
    """Страница входа"""
    return render_template('client_login.html')

@client_app.route('/register', methods=['GET', 'POST'])
def client_register():
    """Регистрация клиента"""
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')

        if not name or not phone:
            flash('Имя и телефон обязательны для заполнения', 'error')
            return render_template('client_register.html')

        try:
            response = requests.post(f"{ADMIN_SERVER_URL}/api/client/register", json={
                'name': name,
                'phone': phone,
                'email': email
            })
            if response.status_code == 200:
                data = response.json()
                session['client_id'] = data['client_id']
                session['client_name'] = name
                flash('Регистрация прошла успешно!', 'success')
                return redirect(url_for('client_dashboard'))
            else:
                error_data = response.json()
                flash(error_data.get('message', 'Ошибка регистрации'), 'error')
        except requests.RequestException:
            flash('Ошибка соединения с сервером', 'error')

    return render_template('client_register.html')

@client_app.route('/login', methods=['POST'])
def client_login():
    """Авторизация клиента по телефону"""
    phone = request.form.get('phone')
    if not phone:
        flash('Введите номер телефона', 'error')
        return redirect(url_for('client_index'))

    try:
        response = requests.post(f"{ADMIN_SERVER_URL}/api/client/login", json={'phone': phone})
        if response.status_code == 200:
            data = response.json()
            session['client_id'] = data['client_id']
            session['client_name'] = data['name']
            return redirect(url_for('client_dashboard'))
        else:
            error_data = response.json()
            flash(error_data.get('message', 'Клиент не найден'), 'error')
    except requests.RequestException:
        flash('Ошибка соединения с сервером', 'error')

    return redirect(url_for('client_index'))

@client_app.route('/dashboard')
def client_dashboard():
    """Дашборд клиента"""
    if 'client_id' not in session:
        return redirect(url_for('client_index'))

    try:
        client_resp = requests.get(f"{ADMIN_SERVER_URL}/api/client/{session['client_id']}")
        computers_resp = requests.get(f"{ADMIN_SERVER_URL}/api/computers")

        if client_resp.status_code == 200 and computers_resp.status_code == 200:
            client_data = client_resp.json()
            computers_data = computers_resp.json()
            return render_template('client_dashboard.html', client=client_data, computers=computers_data)
        else:
            flash('Ошибка загрузки данных', 'error')
            return redirect(url_for('client_index'))
    except requests.RequestException:
        flash('Ошибка соединения с сервером', 'error')
        return redirect(url_for('client_index'))

@client_app.route('/book_computer', methods=['POST'])
def client_book_computer():
    """Бронирование компьютера"""
    if 'client_id' not in session:
        return redirect(url_for('client_index'))

    computer_id = request.form.get('computer_id')
    duration_hours = request.form.get('duration_hours')

    if not computer_id or not duration_hours:
        flash('Выберите компьютер и укажите время бронирования', 'error')
        return redirect(url_for('client_dashboard'))

    try:
        response = requests.post(f"{ADMIN_SERVER_URL}/api/client/book", json={
            'client_id': session['client_id'],
            'computer_id': computer_id,
            'duration_hours': float(duration_hours)
        })
        if response.status_code == 200:
            flash('Бронирование создано успешно!', 'success')
        else:
            error_data = response.json()
            flash(error_data.get('message', 'Ошибка бронирования'), 'error')
    except requests.RequestException:
        flash('Ошибка соединения с сервером', 'error')

    return redirect(url_for('client_dashboard'))

@client_app.route('/logout')
def client_logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('client_index'))

if __name__ == '__main__':
    client_app.run(host='0.0.0.0', port=5001, debug=True)
