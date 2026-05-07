import os
from flask import Flask, jsonify
from app.extensions import db
from app.exceptions import AppError


def create_app(config=None):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'postgresql://bank:bank@localhost:5432/bankdb'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if config:
        app.config.update(config)
    db.init_app(app)

    from app.routes.users import users_bp
    from app.routes.accounts import accounts_bp
    from app.routes.transactions import transactions_bp
    from app.routes.cards import cards_bp
    from app.routes.loans import loans_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(accounts_bp, url_prefix='/api/accounts')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(cards_bp, url_prefix='/api/cards')
    app.register_blueprint(loans_bp, url_prefix='/api/loans')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')

    @app.errorhandler(AppError)
    def handle_app_error(e):
        return jsonify({'error': e.message}), e.status_code

    return app
