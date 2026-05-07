from app.extensions import db
from app.models import User, Account
from app.exceptions import (
    NotFoundError, EmailAlreadyExistsError,
    UserHasActiveAccountsError, AlreadyVerifiedError,
)
from app.utils import validate_email, paginate
from app.exceptions import InvalidAmountError


def create_user(name: str, email: str) -> User:
    if not validate_email(email):
        raise InvalidAmountError(f'Invalid email format: {email}')
    if User.query.filter_by(email=email).first():
        raise EmailAlreadyExistsError(f'Email already exists: {email}')
    user = User(name=name, email=email)
    db.session.add(user)
    db.session.commit()
    return user


def get_user(user_id: int) -> User:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(f'User {user_id} not found')
    return user


def get_all_users(page: int = 1, per_page: int = 20) -> dict:
    return paginate(User.query, page, per_page)


def update_user(user_id: int, name: str = None, email: str = None) -> User:
    user = get_user(user_id)
    if email and email != user.email:
        if not validate_email(email):
            raise InvalidAmountError(f'Invalid email format: {email}')
        if User.query.filter_by(email=email).first():
            raise EmailAlreadyExistsError(f'Email already exists: {email}')
        user.email = email
    if name:
        user.name = name
    db.session.commit()
    return user


def delete_user(user_id: int) -> None:
    user = get_user(user_id)
    active_accounts = Account.query.filter_by(user_id=user_id).filter(
        Account.status != 'closed'
    ).count()
    if active_accounts > 0:
        raise UserHasActiveAccountsError(
            f'User {user_id} has active accounts and cannot be deleted'
        )
    db.session.delete(user)
    db.session.commit()


def verify_email(user_id: int) -> User:
    user = get_user(user_id)
    if user.is_email_verified:
        raise AlreadyVerifiedError(f'User {user_id} email is already verified')
    user.is_email_verified = True
    db.session.commit()
    return user


def search_users(q: str) -> list:
    pattern = f'%{q}%'
    return User.query.filter(
        (User.name.ilike(pattern)) | (User.email.ilike(pattern))
    ).all()


def get_user_summary(user_id: int) -> dict:
    user = get_user(user_id)
    accounts = Account.query.filter_by(user_id=user_id).all()
    total_balance = sum(float(a.balance) for a in accounts)
    return {
        'user': user.to_dict(),
        'accounts': [a.to_dict() for a in accounts],
        'total_balance': total_balance,
        'account_count': len(accounts),
    }
