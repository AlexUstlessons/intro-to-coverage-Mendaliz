from decimal import Decimal
from app.extensions import db
from app.models import Account, Transaction, User
from app.exceptions import (
    NotFoundError, AccountFrozenError, AccountClosedError,
    AccountNotFrozenError, AccountNotEmptyError,
    InsufficientFundsError, InvalidAmountError,
    OverdraftNotAllowedError, MinimumBalanceError,
    DailyLimitExceededError, InvalidAccountTypeError,
)

VALID_ACCOUNT_TYPES = {'checking', 'savings', 'investment'}
SAVINGS_MINIMUM_BALANCE = Decimal('10.00')


def get_account(account_id: int) -> Account:
    account = Account.query.get(account_id)
    if not account:
        raise NotFoundError(f'Account {account_id} not found')
    return account


def create_account(user_id: int, account_type: str) -> Account:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(f'User {user_id} not found')
    if account_type not in VALID_ACCOUNT_TYPES:
        raise InvalidAccountTypeError(f'Invalid account type: {account_type}')
    account = Account(user_id=user_id, type=account_type)
    db.session.add(account)
    db.session.commit()
    return account


def get_user_accounts(user_id: int) -> list:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(f'User {user_id} not found')
    return Account.query.filter_by(user_id=user_id).all()


def deposit(account_id: int, amount: float) -> Account:
    account = get_account(account_id)
    amount = Decimal(str(amount))
    if amount <= 0:
        raise InvalidAmountError('Deposit amount must be positive')
    if account.status == 'frozen':
        raise AccountFrozenError('Account is frozen')
    if account.status == 'closed':
        raise AccountClosedError('Account is closed')
    if amount > account.daily_deposit_limit:
        raise DailyLimitExceededError(
            f'Amount exceeds daily deposit limit of {account.daily_deposit_limit}'
        )
    account.balance += amount
    tx = Transaction(to_account_id=account_id, amount=amount, type='deposit', status='completed')
    db.session.add(tx)
    db.session.commit()
    return account


def withdraw(account_id: int, amount: float) -> Account:
    account = get_account(account_id)
    amount = Decimal(str(amount))
    if amount <= 0:
        raise InvalidAmountError('Withdrawal amount must be positive')
    if account.status == 'frozen':
        raise AccountFrozenError('Account is frozen')
    if account.status == 'closed':
        raise AccountClosedError('Account is closed')
    if account.type == 'savings' and (account.balance - amount) < SAVINGS_MINIMUM_BALANCE:
        raise MinimumBalanceError(
            f'Savings accounts must maintain a minimum balance of {SAVINGS_MINIMUM_BALANCE}'
        )
    if account.balance < amount:
        if not account.overdraft_enabled:
            raise InsufficientFundsError('Insufficient funds')
    account.balance -= amount
    tx = Transaction(from_account_id=account_id, amount=amount, type='withdrawal', status='completed')
    db.session.add(tx)
    db.session.commit()
    return account


def freeze_account(account_id: int) -> Account:
    account = get_account(account_id)
    if account.status == 'frozen':
        raise AccountFrozenError('Account is already frozen')
    if account.status == 'closed':
        raise AccountClosedError('Account is closed')
    account.status = 'frozen'
    db.session.commit()
    return account


def unfreeze_account(account_id: int) -> Account:
    account = get_account(account_id)
    if account.status != 'frozen':
        raise AccountNotFrozenError('Account is not frozen')
    account.status = 'active'
    db.session.commit()
    return account


def close_account(account_id: int) -> Account:
    account = get_account(account_id)
    if account.status == 'closed':
        raise AccountClosedError('Account is already closed')
    if account.balance != Decimal('0.00'):
        raise AccountNotEmptyError('Account balance must be zero to close')
    account.status = 'closed'
    db.session.commit()
    return account


def set_overdraft(account_id: int, enabled: bool) -> Account:
    account = get_account(account_id)
    if enabled and account.type == 'investment':
        raise OverdraftNotAllowedError('Investment accounts cannot have overdraft enabled')
    account.overdraft_enabled = enabled
    db.session.commit()
    return account


def get_balance_history(account_id: int) -> list:
    get_account(account_id)  # raises if not found
    return Transaction.query.filter(
        (Transaction.from_account_id == account_id) |
        (Transaction.to_account_id == account_id)
    ).order_by(Transaction.created_at).all()


def get_statement(account_id: int, from_date=None, to_date=None) -> list:
    get_account(account_id)
    query = Transaction.query.filter(
        (Transaction.from_account_id == account_id) |
        (Transaction.to_account_id == account_id)
    )
    if from_date:
        query = query.filter(Transaction.created_at >= from_date)
    if to_date:
        query = query.filter(Transaction.created_at <= to_date)
    return query.order_by(Transaction.created_at).all()


def bulk_deposit(deposits: list) -> list:
    results = []
    for item in deposits:
        account = deposit(item['account_id'], item['amount'])
        results.append(account)
    return results
