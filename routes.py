from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from models import Computer, Client, Booking, Tariff, Transaction
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from zoneinfo import ZoneInfo


def _activate_scheduled_bookings():
    """Автоматически активирует запланированные бронирования, время которых наступило"""
    now = datetime.now()

    # Найти все запланированные бронирования, время которых уже наступило
    scheduled_bookings = Booking.query.filter(
        Booking.status == 'scheduled',
        Booking.start_time <= now
    ).all()

    for booking in scheduled_bookings:
        # Проверить, что компьютер все еще доступен
        if booking.computer.status == 'available':
            # Активировать бронирование
            booking.status = 'active'
            booking.computer.status = 'occupied'
            booking.computer.current_client_id = booking.client_id
            booking.computer.session_start = now

    if scheduled_bookings:
        db.session.commit()

@app.route('/')
def index():
    return redirect(url_for('admin_dashboard'))


@app.route('/admin')
def admin_dashboard():
    # Автоматическая активация запланированных бронирований
    _activate_scheduled_bookings()

    # Статистика для дашборда
    total_computers = Computer.query.count()
    occupied_computers = Computer.query.filter_by(status='occupied').count()
    available_computers = total_computers - occupied_computers

    # Доходы
    today = datetime.now().date()
    today_revenue = db.session.query(func.sum(Transaction.amount)).filter(
        func.date(Transaction.created_at) == today,
        Transaction.transaction_type == 'payment'
    ).scalar() or 0

    total_revenue = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == 'payment'
    ).scalar() or 0

    # Активные бронирования
    active_bookings = Booking.query.filter_by(status='active').count()

    # Клиенты
    total_clients = Client.query.count()

    # Текущие сессии
    current_sessions = Computer.query.filter_by(status='occupied').all()

    return render_template('admin/dashboard.html',
                           total_computers=total_computers,
                           occupied_computers=occupied_computers,
                           available_computers=available_computers,
                           today_revenue=today_revenue,
                           total_revenue=total_revenue,
                           active_bookings=active_bookings,
                           total_clients=total_clients,
                           current_sessions=current_sessions)


@app.route('/admin/computers')
def admin_computers():
    computers = Computer.query.all()
    return render_template('admin/computers.html', computers=computers)


@app.route('/admin/computers/<int:computer_id>/start', methods=['POST'])
def start_computer_session(computer_id):
    computer = Computer.query.get_or_404(computer_id)
    client_name = request.form.get('client_name')

    if not client_name:
        flash('Необходимо указать имя клиента', 'error')
        return redirect(url_for('admin_computers'))

    # Найти или создать клиента
    client = Client.query.filter_by(name=client_name).first()
    if not client:
        client = Client(name=client_name)
        db.session.add(client)
        db.session.flush()  # Получить ID клиента

    # Запустить сессию
    computer.status = 'occupied'
    computer.current_client_id = client.id
    computer.session_start = datetime.now()

    # Создать бронирование
    booking = Booking(
        client_id=client.id,
        computer_id=computer.id,
        start_time=datetime.now(),
        planned_duration=1.0,  # По умолчанию 1 час
        status='active'
    )
    db.session.add(booking)

    db.session.commit()
    flash(f'Сессия запущена для {client_name} на {computer.name}', 'success')
    return redirect(url_for('admin_computers'))


@app.route('/admin/computers/<int:computer_id>/stop', methods=['POST'])
def stop_computer_session(computer_id):
    computer = Computer.query.get_or_404(computer_id)

    if computer.status != 'occupied':
        flash('Компьютер не занят', 'error')
        return redirect(url_for('admin_computers'))

    # Рассчитать время и стоимость
    duration = computer.get_current_session_duration()
    cost = computer.get_current_cost()

    # Найти активное бронирование
    booking = Booking.query.filter_by(
        computer_id=computer.id,
        status='active'
    ).first()

    if booking:
        booking.end_time = datetime.now()
        booking.actual_duration = duration
        booking.total_cost = cost
        booking.status = 'completed'

        # Создать транзакцию
        transaction = Transaction(
            client_id=booking.client_id,
            booking_id=booking.id,
            amount=cost,
            transaction_type='payment',
            description=f'Оплата за {duration:.2f} ч. на {computer.name}'
        )
        db.session.add(transaction)

        # Обновить статистику клиента
        client = booking.client
        client.total_spent += cost

    # Остановить сессию
    computer.status = 'available'
    computer.current_client_id = None
    computer.total_hours_today += duration
    computer.session_start = None

    db.session.commit()
    flash(f'Сессия завершена. Время: {duration:.2f} ч., Сумма: {cost:.2f} ₽', 'success')
    return redirect(url_for('admin_computers'))


@app.route('/admin/bookings')
def admin_bookings():
    # Автоматическая активация запланированных бронирований
    _activate_scheduled_bookings()

    bookings = Booking.query.order_by(Booking.created_at.desc()).all()

    # Получаем фильтры из параметров запроса
    status_filter = request.args.get('status')
    client_filter = request.args.get('client')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Базовый запрос
    query = Booking.query

    # Применяем фильтры
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    return render_template('admin/bookings.html', bookings=bookings)


@app.route('/admin/bookings/<int:booking_id>')
def booking_details(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template('admin/booking_details.html', booking=booking)


@app.route('/admin/bookings/<int:booking_id>/edit', methods=['GET', 'POST'])
def edit_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if request.method == 'POST':
        # Получаем данные из формы
        planned_duration = float(request.form.get('planned_duration', booking.planned_duration))
        start_time_str = request.form.get('start_time')
        status = request.form.get('status', booking.status)

        # Обновляем время начала если указано
        if start_time_str:
            try:
                new_start_time = datetime.fromisoformat(start_time_str)
                booking.start_time = new_start_time
            except ValueError:
                flash('Неверный формат времени', 'error')
                return redirect(url_for('edit_booking', booking_id=booking_id))

        # Обновляем данные
        booking.planned_duration = planned_duration
        old_status = booking.status
        booking.status = status

        # Если статус изменился с scheduled на active
        if old_status == 'scheduled' and status == 'active':
            if booking.computer.status == 'available':
                booking.computer.status = 'occupied'
                booking.computer.current_client_id = booking.client_id
                booking.computer.session_start = datetime.now()
            else:
                flash('Компьютер не доступен для активации', 'error')
                return redirect(url_for('edit_booking', booking_id=booking_id))

        # Если статус изменился с active на другой
        elif old_status == 'active' and status != 'active':
            booking.computer.status = 'available'
            booking.computer.current_client_id = None
            booking.computer.session_start = None

        db.session.commit()
        flash('Бронирование обновлено', 'success')
        return redirect(url_for('booking_details', booking_id=booking_id))

    return render_template('admin/edit_booking.html', booking=booking)


@app.route('/admin/bookings/create')
def create_booking():
    computers = Computer.query.filter_by(status='available').all()
    clients = Client.query.filter_by(is_active=True).all()
    tz = ZoneInfo("Asia/Tokyo")  # UTC+9
    current_time = datetime.now(tz)
    return render_template('admin/create_booking.html', computers=computers, clients=clients,current_time=current_time)


@app.route('/admin/bookings/create', methods=['POST'])
def create_booking_post():
    client_name = request.form.get('client_name')
    new_client_name = request.form.get('new_client_name')
    computer_id = request.form.get('computer_id')
    planned_duration = float(request.form.get('planned_duration', 1.0))
    start_immediately = request.form.get('start_immediately') == 'on'
    scheduled_time = request.form.get('scheduled_time')

    # Определить клиента
    if new_client_name:
        client = Client(name=new_client_name)
        db.session.add(client)
        db.session.flush()
    else:
        client = Client.query.filter_by(name=client_name).first()
        if not client:
            flash('Клиент не найден', 'error')
            return redirect(url_for('create_booking'))

    computer = Computer.query.get_or_404(computer_id)

    # Определить время начала
    if start_immediately:
        start_time = datetime.now()
        status = 'active'
    else:
        if scheduled_time:
            try:
                start_time = datetime.fromisoformat(scheduled_time)
            except ValueError:
                flash('Неверный формат времени', 'error')
                return redirect(url_for('create_booking'))
        else:
            start_time = datetime.now()
        status = 'scheduled'

    # Создать бронирование
    booking = Booking(
        client_id=client.id,
        computer_id=computer.id,
        start_time=start_time,
        planned_duration=planned_duration,
        status=status
    )
    db.session.add(booking)

    # Если начать немедленно
    if start_immediately:
        computer.status = 'occupied'
        computer.current_client_id = client.id
        computer.session_start = datetime.now()

    db.session.commit()
    flash('Бронирование создано успешно', 'success')
    return redirect(url_for('admin_bookings'))


@app.route('/admin/clients')
def admin_clients():
    clients = Client.query.order_by(Client.registration_date.desc()).all()
    return render_template('admin/clients.html', clients=clients)


@app.route('/admin/clients/create', methods=['POST'])
def create_client():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')

    client = Client(name=name, email=email, phone=phone)
    db.session.add(client)
    db.session.commit()

    flash('Клиент добавлен успешно', 'success')
    return redirect(url_for('admin_clients'))


@app.route('/admin/reports')
def admin_reports():
    # Статистика по дням
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    # Доходы по дням
    daily_revenue = db.session.query(
        func.date(Transaction.created_at).label('date'),
        func.sum(Transaction.amount).label('revenue')
    ).filter(
        Transaction.transaction_type == 'payment',
        func.date(Transaction.created_at) >= week_ago
    ).group_by(func.date(Transaction.created_at)).all()

    daily_revenue_formatted = [
        (day[0].strftime("%d.%m") if hasattr(day[0], 'strftime') else day[0], day[1])
        for day in daily_revenue
    ]

    # Популярные компьютеры
    popular_computers = db.session.query(
        Computer.name,
        func.count(Booking.id).label('bookings_count'),
        func.sum(Booking.actual_duration).label('total_hours')
    ).join(Booking).filter(
        func.date(Booking.created_at) >= week_ago
    ).group_by(Computer.id).order_by(func.count(Booking.id).desc()).all()

    # Топ клиенты
    top_clients = db.session.query(
        Client.name,
        func.sum(Transaction.amount).label('total_spent'),
        func.count(Transaction.id).label('visits_count')
    ).join(Transaction, Transaction.client_id == Client.id).filter(
        func.date(Transaction.created_at) >= week_ago
    ).group_by(Client.id).order_by(func.sum(Transaction.amount).desc()).limit(10).all()

    return render_template('admin/reports.html',
                           daily_revenue=daily_revenue_formatted,
                           popular_computers=popular_computers,
                           top_clients=top_clients,
                           datetime=datetime)


# Клиентские маршруты
@app.route('/client/login')
def client_login():
    return render_template('client/login.html')


@app.route('/client/login', methods=['POST'])
def client_login_post():
    name = request.form.get('name')

    client = Client.query.filter_by(name=name).first()
    if not client:
        client = Client(name=name)
        db.session.add(client)
        db.session.commit()

    return redirect(url_for('client_dashboard', client_id=client.id))


@app.route('/client/<int:client_id>/dashboard')
def client_dashboard(client_id):
    client = Client.query.get_or_404(client_id)

    # Активные бронирования
    active_bookings = Booking.query.filter_by(
        client_id=client_id,
        status='active'
    ).all()

    # История
    history = Booking.query.filter_by(
        client_id=client_id
    ).order_by(Booking.created_at.desc()).limit(10).all()

    return render_template('client/dashboard.html',
                           client=client,
                           active_bookings=active_bookings,
                           history=history)


# API endpoints для AJAX
@app.route('/api/computers/status')
def api_computers_status():
    computers = Computer.query.all()
    data = []
    for computer in computers:
        data.append({
            'id': computer.id,
            'name': computer.name,
            'status': computer.status,
            'current_client': computer.current_client.name if computer.current_client else None,
            'session_duration': computer.get_current_session_duration(),
            'current_cost': computer.get_current_cost()
        })
    return jsonify(data)


# API для клиентского терминала
@app.route('/api/client/register', methods=['POST'])
def api_client_register():
    """API регистрации клиента"""
    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')

    if not name or not phone:
        return jsonify({'message': 'Имя и телефон обязательны'}), 400

    # Проверяем уникальность телефона
    existing_client = Client.query.filter_by(phone=phone).first()
    if existing_client:
        return jsonify({'message': 'Клиент с таким телефоном уже существует'}), 400

    client = Client(name=name, phone=phone, email=email)
    db.session.add(client)
    db.session.commit()

    return jsonify({
        'client_id': client.id,
        'message': 'Клиент зарегистрирован успешно'
    })


@app.route('/api/client/login', methods=['POST'])
def api_client_login():
    """API авторизации клиента"""
    data = request.get_json()
    phone = data.get('phone')

    if not phone:
        return jsonify({'message': 'Номер телефона обязателен'}), 400

    client = Client.query.filter_by(phone=phone).first()
    if not client:
        return jsonify({'message': 'Клиент с таким телефоном не найден'}), 404

    return jsonify({
        'client_id': client.id,
        'name': client.name,
        'balance': client.balance
    })


@app.route('/api/client/<int:client_id>')
def api_client_info(client_id):
    """API получения информации о клиенте"""
    client = Client.query.get_or_404(client_id)

    # Получаем доступные компьютеры
    available_computers = Computer.query.filter_by(status='available').all()

    # Получаем активные бронирования клиента
    active_bookings = Booking.query.filter_by(
        client_id=client_id,
        status='active'
    ).all()

    return jsonify({
        'id': client.id,
        'name': client.name,
        'phone': client.phone,
        'balance': client.balance,
        'total_spent': client.total_spent,
        'available_computers': [
            {
                'id': comp.id,
                'name': comp.name,
                'hourly_rate': comp.hourly_rate
            } for comp in available_computers
        ],
        'active_bookings': [
            {
                'id': booking.id,
                'computer_name': booking.computer.name,
                'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M') if booking.end_time else None
            } for booking in active_bookings
        ]
    })


@app.route('/api/client/book', methods=['POST'])
def api_client_book():
    """API бронирования компьютера"""
    data = request.get_json()
    client_id = data.get('client_id')
    computer_id = data.get('computer_id')
    duration_hours = float(data.get('duration_hours', 1))

    client = Client.query.get_or_404(client_id)
    computer = Computer.query.get_or_404(computer_id)

    # Рассчитываем стоимость
    total_cost = duration_hours * computer.hourly_rate

    # Проверяем баланс
    if client.balance < total_cost:
        return jsonify({
            'message': f'Недостаточно средств. Нужно {total_cost} руб., доступно {client.balance} руб.'
        }), 400

    # Проверяем доступность компьютера
    if computer.status != 'available':
        return jsonify({'message': 'Компьютер недоступен'}), 400

    # Создаем бронь
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)

    booking = Booking(
        client_id=client_id,
        computer_id=computer_id,
        start_time=start_time,
        end_time=end_time,
        planned_duration=duration_hours,
        total_cost=total_cost,
        status='active'
    )

    # Обновляем статус компьютера
    computer.status = 'occupied'
    computer.current_client_id = client_id
    computer.session_start = start_time

    # Списываем средства
    client.balance -= total_cost

    # Создаем транзакцию оплаты
    transaction = Transaction(
        client_id=client_id,
        booking_id=booking.id,
        amount=-total_cost,
        transaction_type='payment',
        description=f'Оплата за {duration_hours}ч на {computer.name}'
    )

    db.session.add(booking)
    db.session.add(transaction)
    db.session.commit()

    return jsonify({
        'booking_id': booking.id,
        'message': 'Бронирование создано успешно'
    })