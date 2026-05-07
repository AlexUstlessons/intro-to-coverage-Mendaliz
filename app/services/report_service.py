from datetime import datetime
from app.models import Account, Transaction, Loan, User, AuditLog
from app.exceptions import NotFoundError
from app.utils import parse_date_range


def get_user_balance(user_id: int) -> dict:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(f'User {user_id} not found')
    accounts = Account.query.filter_by(user_id=user_id).all()
    total = sum(float(a.balance) for a in accounts)
    return {
        'user_id': user_id,
        'total_balance': total,
        'account_count': len(accounts),
        'accounts': [{'id': a.id, 'type': a.type, 'balance': float(a.balance)} for a in accounts],
    }


def get_transaction_summary() -> dict:
    txs = Transaction.query.all()
    summary = {}
    for tx in txs:
        if tx.type not in summary:
            summary[tx.type] = {'count': 0, 'total': 0.0}
        summary[tx.type]['count'] += 1
        summary[tx.type]['total'] += float(tx.amount)
    return {'total_transactions': len(txs), 'by_type': summary}


def get_top_accounts(limit: int = 10) -> list:
    accounts = Account.query.order_by(Account.balance.desc()).limit(limit).all()
    return [{'id': a.id, 'user_id': a.user_id, 'balance': float(a.balance), 'type': a.type}
            for a in accounts]


def get_revenue() -> dict:
    """Sum interest from paid/approved loans as revenue."""
    loans = Loan.query.filter(Loan.status.in_(['approved', 'paid'])).all()
    total_interest = 0.0
    for loan in loans:
        total_interest += float(loan.monthly_payment) * loan.term_months - float(loan.amount)
    return {'total_interest_revenue': round(total_interest, 2)}


def get_monthly_report(user_id: int, month: int, year: int) -> dict:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(f'User {user_id} not found')
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    accounts = Account.query.filter_by(user_id=user_id).all()
    account_ids = [a.id for a in accounts]
    txs = Transaction.query.filter(
        Transaction.created_at >= start,
        Transaction.created_at < end,
    ).filter(
        (Transaction.from_account_id.in_(account_ids)) |
        (Transaction.to_account_id.in_(account_ids))
    ).all() if account_ids else []
    total_in = sum(float(tx.amount) for tx in txs if tx.to_account_id in account_ids)
    total_out = sum(float(tx.amount) for tx in txs if tx.from_account_id in account_ids)
    return {
        'user_id': user_id,
        'year': year,
        'month': month,
        'transaction_count': len(txs),
        'total_in': total_in,
        'total_out': total_out,
    }


def get_risk_analysis() -> dict:
    overdraft_accounts = Account.query.filter_by(overdraft_enabled=True).all()
    overdue_loans = []
    now = datetime.utcnow()
    from datetime import timedelta
    for loan in Loan.query.filter_by(status='approved').all():
        due = loan.created_at + timedelta(days=loan.term_months * 30)
        if due < now:
            overdue_loans.append(loan)
    return {
        'overdraft_accounts': [a.to_dict() for a in overdraft_accounts],
        'overdue_loans': [loan.to_dict() for loan in overdue_loans],
        'overdraft_count': len(overdraft_accounts),
        'overdue_loan_count': len(overdue_loans),
    }


def get_audit_log(user_id: int = None, action: str = None) -> list:
    query = AuditLog.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter_by(action=action)
    return query.order_by(AuditLog.created_at.desc()).all()


def get_daily_volumes(from_str: str = None, to_str: str = None) -> list:
    from_date, to_date = parse_date_range(from_str, to_str)
    query = Transaction.query
    if from_date:
        query = query.filter(Transaction.created_at >= from_date)
    if to_date:
        query = query.filter(Transaction.created_at <= to_date)
    txs = query.all()
    volumes = {}
    for tx in txs:
        day = tx.created_at.date().isoformat()
        if day not in volumes:
            volumes[day] = {'count': 0, 'total': 0.0}
        volumes[day]['count'] += 1
        volumes[day]['total'] += float(tx.amount)
    return [{'date': d, **v} for d, v in sorted(volumes.items())]
