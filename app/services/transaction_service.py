from decimal import Decimal
from datetime import datetime
from app.extensions import db
from app.models import Transaction
from app.exceptions import (
    NotFoundError, AccountFrozenError, AccountClosedError,
    InsufficientFundsError, InvalidAmountError, TransactionNotCancelableError,
)
from app.services.account_service import get_account


def transfer(from_account_id: int, to_account_id: int, amount: float, description: str = None) -> Transaction:
    if from_account_id == to_account_id:
        raise InvalidAmountError('Cannot transfer to the same account')
    amount = Decimal(str(amount))
    if amount <= 0:
        raise InvalidAmountError('Transfer amount must be positive')
    from_account = get_account(from_account_id)
    to_account = get_account(to_account_id)
    if from_account.status == 'frozen':
        raise AccountFrozenError('Source account is frozen')
    if from_account.status == 'closed':
        raise AccountClosedError('Source account is closed')
    if to_account.status == 'frozen':
        raise AccountFrozenError('Destination account is frozen')
    if to_account.status == 'closed':
        raise AccountClosedError('Destination account is closed')
    if from_account.balance < amount:
        raise InsufficientFundsError('Insufficient funds for transfer')
    from_account.balance -= amount
    to_account.balance += amount
    tx = Transaction(
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        amount=amount,
        type='transfer',
        status='completed',
        description=description,
    )
    db.session.add(tx)
    db.session.commit()
    return tx


def create_deposit(account_id: int, amount: float, description: str = None) -> Transaction:
    amount = Decimal(str(amount))
    if amount <= 0:
        raise InvalidAmountError('Deposit amount must be positive')
    account = get_account(account_id)
    if account.status == 'frozen':
        raise AccountFrozenError('Account is frozen')
    if account.status == 'closed':
        raise AccountClosedError('Account is closed')
    account.balance += amount
    tx = Transaction(
        to_account_id=account_id,
        amount=amount,
        type='deposit',
        status='completed',
        description=description,
    )
    db.session.add(tx)
    db.session.commit()
    return tx


def create_withdrawal(account_id: int, amount: float, description: str = None) -> Transaction:
    amount = Decimal(str(amount))
    if amount <= 0:
        raise InvalidAmountError('Withdrawal amount must be positive')
    account = get_account(account_id)
    if account.status == 'frozen':
        raise AccountFrozenError('Account is frozen')
    if account.status == 'closed':
        raise AccountClosedError('Account is closed')
    if account.balance < amount:
        raise InsufficientFundsError('Insufficient funds')
    account.balance -= amount
    tx = Transaction(
        from_account_id=account_id,
        amount=amount,
        type='withdrawal',
        status='completed',
        description=description,
    )
    db.session.add(tx)
    db.session.commit()
    return tx


def get_transaction(tx_id: int) -> Transaction:
    tx = Transaction.query.get(tx_id)
    if not tx:
        raise NotFoundError(f'Transaction {tx_id} not found')
    return tx


def get_account_transactions(account_id: int, type_filter: str = None,
                             from_date: datetime = None, to_date: datetime = None) -> list:
    get_account(account_id)
    query = Transaction.query.filter(
        (Transaction.from_account_id == account_id) |
        (Transaction.to_account_id == account_id)
    )
    if type_filter:
        query = query.filter(Transaction.type == type_filter)
    if from_date:
        query = query.filter(Transaction.created_at >= from_date)
    if to_date:
        query = query.filter(Transaction.created_at <= to_date)
    return query.order_by(Transaction.created_at.desc()).all()


def cancel_transaction(tx_id: int) -> Transaction:
    tx = get_transaction(tx_id)
    if tx.status != 'pending':
        raise TransactionNotCancelableError(
            f'Only pending transactions can be cancelled, got: {tx.status}'
        )
    tx.status = 'failed'
    db.session.commit()
    return tx


def batch_transfer(from_account_id: int, recipients: list) -> list:
    """Transfer to multiple recipients. All-or-nothing: raises on first failure."""
    results = []
    for recipient in recipients:
        tx = transfer(from_account_id, recipient['account_id'], recipient['amount'])
        results.append(tx)
    return results


def get_daily_stats(target_date: datetime.date) -> dict:
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    txs = Transaction.query.filter(
        Transaction.created_at >= start,
        Transaction.created_at <= end,
    ).all()
    total_amount = sum(float(tx.amount) for tx in txs)
    return {
        'date': target_date.isoformat(),
        'count': len(txs),
        'total_amount': total_amount,
    }


def get_monthly_stats(year: int, month: int) -> dict:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    txs = Transaction.query.filter(
        Transaction.created_at >= start,
        Transaction.created_at < end,
    ).all()
    by_type = {}
    for tx in txs:
        if tx.type not in by_type:
            by_type[tx.type] = {'count': 0, 'total': 0.0}
        by_type[tx.type]['count'] += 1
        by_type[tx.type]['total'] += float(tx.amount)
    return {
        'year': year,
        'month': month,
        'count': len(txs),
        'by_type': by_type,
    }
