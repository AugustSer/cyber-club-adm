import os
import random
import string
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from models import Computer, User, Booking


def generate_access_code():
    """Генерирует уникальный код доступа"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@app.route('/')
def index():
    """Главная страница АРМ администратора"""
    computers = Computer.query.all()
    active_bookings = Booking.query.filter_by(status='active').all()

    # Обновляем статус компьютеров на основе активных броней
    for computer in computers:
        current_booking = None
        for booking in active_bookings:
            if booking.computer_id == computer.id and booking.is_active_now():
                current_booking = booking
                break

        if current_booking:
            computer.status = 'occupied'
        else:
            computer.status = 'available'

    db.session.commit()

    return render_template('index.html',
                           computers=computers,
                           active_bookings=active_bookings,
                           current_time=datetime.now())


@app.route('/add_computer', methods=['POST'])
def add_computer():
    """Добавление нового компьютера"""
    name = request.form.get('name')
    ip_address = request.form.get('ip_address')

    if not name or not ip_address:
        flash('Необходимо заполнить все поля', 'error')
        return redirect(url_for('index'))

    # Проверяем уникальность имени
    existing = Computer.query.filter_by(name=name).first()
    if existing:
        flash('Компьютер с таким именем уже существует', 'error')
        return redirect(url_for('index'))

    computer = Computer(name=name, ip_address=ip_address)
    db.session.add(computer)
    db.session.commit()

    flash(f'Компьютер {name} успешно добавлен', 'success')
    return redirect(url_for('index'))


@app.route('/create_booking', methods=['POST'])
def create_booking():
    """Создание новой брони"""
    username = request.form.get('username')
    phone = request.form.get('phone')
    computer_id = request.form.get('computer_id')
    start_time_str = request.form.get('start_time')
    duration_hours = request.form.get('duration_hours')

    if not all([username, computer_id, start_time_str, duration_hours]):
        flash('Необходимо заполнить все поля', 'error')
        return redirect(url_for('index'))

    try:
        # Парсим время начала
        start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        duration = int(duration_hours)
        end_time = start_time + timedelta(hours=duration)

        # Проверяем, что время начала не в прошлом
        if start_time < datetime.now():
            flash('Время начала не может быть в прошлом', 'error')
            return redirect(url_for('index'))

        # Проверяем доступность компьютера
        computer = Computer.query.get(computer_id)
        if not computer:
            flash('Компьютер не найден', 'error')
            return redirect(url_for('index'))

        # Проверяем конфликты бронирования
        conflicting_booking = Booking.query.filter(
            Booking.computer_id == computer_id,
            Booking.status == 'active',
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).first()

        if conflicting_booking:
            flash('На выбранное время компьютер уже забронирован', 'error')
            return redirect(url_for('index'))

        # Находим или создаем пользователя
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, phone=phone)
            db.session.add(user)
            db.session.flush()  # Получаем ID пользователя

        # Генерируем уникальный код доступа
        access_code = generate_access_code()
        while Booking.query.filter_by(access_code=access_code).first():
            access_code = generate_access_code()

        # Создаем бронь
        booking = Booking(
            user_id=user.id,
            computer_id=computer_id,
            start_time=start_time,
            end_time=end_time,
            access_code=access_code
        )

        db.session.add(booking)
        db.session.commit()

        flash(f'Бронь создана успешно! Код доступа: {access_code}', 'success')

    except ValueError as e:
        flash('Ошибка в формате времени или продолжительности', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при создании брони: {str(e)}', 'error')

    return redirect(url_for('index'))


@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    """Отмена брони"""
    booking = Booking.query.get(booking_id)
    if not booking:
        flash('Бронь не найдена', 'error')
        return redirect(url_for('index'))

    booking.status = 'cancelled'
    db.session.commit()

    flash('Бронь отменена', 'success')
    return redirect(url_for('index'))


@app.route('/api/check_access/<access_code>')
def check_access(access_code):
    """API для проверки доступа по коду (используется клиентским приложением)"""
    booking = Booking.query.filter_by(access_code=access_code).first()

    if not booking:
        return jsonify({
            'access_granted': False,
            'message': 'Неверный код доступа'
        })

    if booking.status != 'active':
        return jsonify({
            'access_granted': False,
            'message': 'Бронь не активна'
        })

    if not booking.is_active_now():
        return jsonify({
            'access_granted': False,
            'message': 'Время брони истекло или еще не наступило'
        })

    return jsonify({
        'access_granted': True,
        'message': 'Доступ разрешен',
        'user': booking.user.username,
        'computer': booking.computer.name,
        'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/server_time')
def server_time():
    """API для получения времени сервера (для синхронизации)"""
    return jsonify({
        'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'utc_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })


if __name__ == '__main__':
    # Создаем тестовые данные при первом запуске
    with app.app_context():
        if Computer.query.count() == 0:
            test_computers = [
                Computer(name='PC-01', ip_address='192.168.1.101'),
                Computer(name='PC-02', ip_address='192.168.1.102'),
                Computer(name='PC-03', ip_address='192.168.1.103'),
                Computer(name='PC-04', ip_address='192.168.1.104'),
                Computer(name='PC-05', ip_address='192.168.1.105'),
            ]
            for comp in test_computers:
                db.session.add(comp)
            db.session.commit()
            print("Созданы тестовые компьютеры")

    app.run(host='0.0.0.0', port=5000, debug=True)
