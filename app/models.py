from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    accounts = db.relationship('Account', backref='user', lazy=True)
    loans = db.relationship('Loan', backref='user', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'is_email_verified': self.is_email_verified,
            'created_at': self.created_at.isoformat(),
        }


class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    balance = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # checking, savings, investment
    status = db.Column(db.String(20), default='active', nullable=False)  # active, frozen, closed
    overdraft_enabled = db.Column(db.Boolean, default=False, nullable=False)
    daily_deposit_limit = db.Column(db.Numeric(14, 2), default=10000, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cards = db.relationship('Card', backref='account', lazy=True)
    sent_transactions = db.relationship(
        'Transaction', foreign_keys='Transaction.from_account_id',
        backref='from_account', lazy=True
    )
    received_transactions = db.relationship(
        'Transaction', foreign_keys='Transaction.to_account_id',
        backref='to_account', lazy=True
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'balance': float(self.balance),
            'type': self.type,
            'status': self.status,
            'overdraft_enabled': self.overdraft_enabled,
            'daily_deposit_limit': float(self.daily_deposit_limit),
            'created_at': self.created_at.isoformat(),
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    to_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # deposit, withdrawal, transfer
    status = db.Column(db.String(20), default='completed', nullable=False)  # completed, failed, pending
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'from_account_id': self.from_account_id,
            'to_account_id': self.to_account_id,
            'amount': float(self.amount),
            'type': self.type,
            'status': self.status,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
        }


class Card(db.Model):
    __tablename__ = 'cards'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    number = db.Column(db.String(16), unique=True, nullable=False)
    cvv_hash = db.Column(db.String(64), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    is_stolen = db.Column(db.Boolean, default=False, nullable=False)
    daily_limit = db.Column(db.Numeric(14, 2), default=1000, nullable=False)
    daily_spent = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'number': self.number,
            'expiry_date': self.expiry_date.isoformat(),
            'is_active': self.is_active,
            'is_stolen': self.is_stolen,
            'daily_limit': float(self.daily_limit),
            'daily_spent': float(self.daily_spent),
            'created_at': self.created_at.isoformat(),
        }


class Loan(db.Model):
    __tablename__ = 'loans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(6, 4), nullable=False)  # e.g. 0.05 = 5%
    term_months = db.Column(db.Integer, nullable=False)
    monthly_payment = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected, paid
    amount_paid = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'interest_rate': float(self.interest_rate),
            'term_months': self.term_months,
            'monthly_payment': float(self.monthly_payment),
            'status': self.status,
            'amount_paid': float(self.amount_paid),
            'created_at': self.created_at.isoformat(),
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'created_at': self.created_at.isoformat(),
        }
