import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///computer_club.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models and routes
    import models
    import routes



    # Create all tables
    db.create_all()

    # Initialize default data if database is empty
    if models.Computer.query.count() == 0:
        # Create default computers
        for i in range(1, 21):  # 20 компьютеров
            computer = models.Computer(
                name=f"PC-{i:02d}",
                status="available",
                hourly_rate=150.0 if i <= 10 else 200.0  # Разные тарифы
            )
            db.session.add(computer)

        # Create default tariffs
        tariffs = [
            models.Tariff(name="Стандартный", hourly_rate=150.0, description="Обычные компьютеры"),
            models.Tariff(name="Премиум", hourly_rate=200.0, description="Игровые компьютеры"),
            models.Tariff(name="VIP", hourly_rate=300.0, description="Топовые компьютеры")
        ]

        for tariff in tariffs:
            db.session.add(tariff)

        db.session.commit()
        logging.info("Database initialized with default data")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
