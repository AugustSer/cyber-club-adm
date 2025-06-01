from app import db
from datetime import datetime
from sqlalchemy import func


class Computer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="available")  # available, occupied, maintenance
    hourly_rate = db.Column(db.Float, nullable=False)
    current_client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    session_start = db.Column(db.DateTime, nullable=True)
    total_hours_today = db.Column(db.Float, default=0.0)

    # Relationships
    current_client = db.relationship('Client', backref='current_computers')
    bookings = db.relationship('Booking', backref='computer', lazy=True)

    def __repr__(self):
        return f'<Computer {self.name}>'

    def get_current_session_duration(self):
        if self.session_start:
            return (datetime.now() - self.session_start).total_seconds() / 3600
        return 0

    def get_current_cost(self):
        return self.get_current_session_duration() * self.hourly_rate


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    total_spent = db.Column(db.Float, default=0.0)
    total_time_minutes = db.Column(db.Integer, default=0)
    last_visit = db.Column(db.DateTime, nullable=True)
    registration_date = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    bookings = db.relationship('Booking', backref='client', lazy=True)

    def __repr__(self):
        return f'<Client {self.name}>'

    def get_recent_sessions(self, limit=5):
        """Получить последние сессии клиента"""
        return Booking.query.filter_by(client_id=self.id) \
            .order_by(Booking.created_at.desc()) \
            .limit(limit).all()

    def get_total_sessions(self):
        """Общее количество сессий"""
        return Booking.query.filter_by(client_id=self.id, status='completed').count()

    def update_stats(self):
        """Обновить статистику клиента"""
        completed_bookings = Booking.query.filter_by(client_id=self.id, status='completed').all()

        self.total_spent = sum(booking.total_cost or 0 for booking in completed_bookings)
        self.total_time_minutes = sum(int((booking.actual_duration or 0) * 60) for booking in completed_bookings)

        if completed_bookings:
            self.last_visit = max(booking.end_time for booking in completed_bookings if booking.end_time)

        db.session.commit()


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    computer_id = db.Column(db.Integer, db.ForeignKey('computer.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    planned_duration = db.Column(db.Float, nullable=False)  # в часах
    actual_duration = db.Column(db.Float, nullable=True)
    total_cost = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default="active")  # active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Booking {self.id}>'

    def calculate_cost(self):
        if self.actual_duration:
            return self.actual_duration * self.computer.hourly_rate
        return self.planned_duration * self.computer.hourly_rate


class Tariff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    hourly_rate = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Tariff {self.name}>'


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # payment, refund, topup
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    client = db.relationship('Client', backref='transactions')
    booking = db.relationship('Booking', backref='transactions')

    def __repr__(self):
        return f'<Transaction {self.id}>'
