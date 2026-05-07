from decimal import Decimal
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Loan, User
from app.exceptions import (
    NotFoundError, LoanAlreadyPaidError, LoanNotApprovedError,
    LoanNotPendingError, InsufficientFundsError, InvalidAmountError,
)
from app.utils import calculate_monthly_payment, calculate_loan_schedule
from app.services.account_service import get_account


def apply_for_loan(user_id: int, amount: float, interest_rate: float, term_months: int) -> Loan:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(f'User {user_id} not found')
    if amount <= 0:
        raise InvalidAmountError('Loan amount must be positive')
    if interest_rate < 0:
        raise InvalidAmountError('Interest rate cannot be negative')
    if term_months <= 0:
        raise InvalidAmountError('Term must be at least 1 month')
    monthly = calculate_monthly_payment(float(amount), float(interest_rate), term_months)
    loan = Loan(
        user_id=user_id,
        amount=Decimal(str(amount)),
        interest_rate=Decimal(str(interest_rate)),
        term_months=term_months,
        monthly_payment=Decimal(str(monthly)),
        status='pending',
        amount_paid=Decimal('0.00'),
    )
    db.session.add(loan)
    db.session.commit()
    return loan


def get_loan(loan_id: int) -> Loan:
    loan = Loan.query.get(loan_id)
    if not loan:
        raise NotFoundError(f'Loan {loan_id} not found')
    return loan


def get_user_loans(user_id: int) -> list:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError(f'User {user_id} not found')
    return Loan.query.filter_by(user_id=user_id).all()


def approve_loan(loan_id: int) -> Loan:
    loan = get_loan(loan_id)
    if loan.status != 'pending':
        raise LoanNotPendingError(f'Loan must be pending to approve, got: {loan.status}')
    loan.status = 'approved'
    db.session.commit()
    return loan


def reject_loan(loan_id: int) -> Loan:
    loan = get_loan(loan_id)
    if loan.status != 'pending':
        raise LoanNotPendingError(f'Loan must be pending to reject, got: {loan.status}')
    loan.status = 'rejected'
    db.session.commit()
    return loan


def make_payment(loan_id: int, account_id: int) -> Loan:
    loan = get_loan(loan_id)
    if loan.status == 'paid':
        raise LoanAlreadyPaidError(f'Loan {loan_id} is already paid off')
    if loan.status != 'approved':
        raise LoanNotApprovedError(f'Loan {loan_id} must be approved to make payments')
    account = get_account(account_id)
    if account.balance < loan.monthly_payment:
        raise InsufficientFundsError('Insufficient funds to make loan payment')
    account.balance -= loan.monthly_payment
    loan.amount_paid += loan.monthly_payment
    if loan.amount_paid >= loan.amount:
        loan.status = 'paid'
    db.session.commit()
    return loan


def get_payment_schedule(loan_id: int) -> list:
    loan = get_loan(loan_id)
    return calculate_loan_schedule(
        float(loan.amount),
        float(loan.interest_rate),
        loan.term_months,
    )


def early_repayment(loan_id: int, account_id: int) -> Loan:
    loan = get_loan(loan_id)
    if loan.status == 'paid':
        raise LoanAlreadyPaidError(f'Loan {loan_id} is already paid off')
    if loan.status != 'approved':
        raise LoanNotApprovedError(f'Loan {loan_id} must be approved for early repayment')
    remaining = loan.amount - loan.amount_paid
    account = get_account(account_id)
    if account.balance < remaining:
        raise InsufficientFundsError('Insufficient funds for early repayment')
    account.balance -= remaining
    loan.amount_paid = loan.amount
    loan.status = 'paid'
    db.session.commit()
    return loan


def get_overdue_loans() -> list:
    """Return approved loans where created_at + term_months*30 days < now."""
    all_approved = Loan.query.filter_by(status='approved').all()
    overdue = []
    now = datetime.utcnow()
    for loan in all_approved:
        due_date = loan.created_at + timedelta(days=loan.term_months * 30)
        if due_date < now:
            overdue.append(loan)
    return overdue
