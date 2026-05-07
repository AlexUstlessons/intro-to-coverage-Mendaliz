import hashlib
import random
import re
from datetime import date, datetime


def validate_email(email: str) -> bool:
    """Return True if email matches basic format: local@domain.tld"""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def generate_card_number() -> str:
    """Generate a random 16-digit Luhn-valid card number."""
    digits = [random.randint(0, 9) for _ in range(15)]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    check = (10 - total % 10) % 10
    return ''.join(str(d) for d in digits + [check])


def validate_luhn(number: str) -> bool:
    """Validate a card number string using the Luhn algorithm."""
    digits = [int(c) for c in number if c.isdigit()]
    if not digits:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def calculate_monthly_payment(principal: float, rate: float, term: int) -> float:
    """Calculate annuity monthly payment. rate is annual (e.g. 0.12 = 12%).
    If rate is 0, divides principal evenly."""
    if rate == 0:
        return round(principal / term, 2)
    monthly_rate = rate / 12
    payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** (-term))
    return round(payment, 2)


def calculate_loan_schedule(principal: float, rate: float, term: int) -> list:
    """Return list of dicts: month, payment, principal_part, interest, remaining."""
    monthly_payment = calculate_monthly_payment(principal, rate, term)
    schedule = []
    remaining = float(principal)
    for month in range(1, term + 1):
        interest = round(remaining * (rate / 12), 2)
        principal_part = round(monthly_payment - interest, 2)
        remaining = round(remaining - principal_part, 2)
        if month == term:
            remaining = 0.0
        schedule.append({
            'month': month,
            'payment': monthly_payment,
            'principal': principal_part,
            'interest': interest,
            'remaining': remaining,
        })
    return schedule


def hash_cvv(cvv: str) -> str:
    """SHA-256 hash of CVV string."""
    return hashlib.sha256(cvv.encode()).hexdigest()


def verify_cvv(cvv: str, hashed: str) -> bool:
    """Return True if CVV matches the stored hash."""
    return hash_cvv(cvv) == hashed


def is_card_expired(expiry_date: date) -> bool:
    """Return True if expiry_date is before today."""
    return expiry_date < date.today()


def paginate(query, page: int, per_page: int) -> dict:
    """Paginate a SQLAlchemy query. Returns {items, total, page, pages}."""
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, -(-total // per_page))  # ceiling division
    return {'items': items, 'total': total, 'page': page, 'pages': pages}


def parse_date_range(from_str: str | None, to_str: str | None):
    """Parse YYYY-MM-DD strings to datetime objects. Returns (from_dt, to_dt).
    Either or both may be None."""
    fmt = '%Y-%m-%d'
    from_dt = datetime.strptime(from_str, fmt) if from_str else None
    to_dt = datetime.strptime(to_str, fmt) if to_str else None
    return from_dt, to_dt


def format_currency(amount: float) -> str:
    """Format float as dollar string: $1234.56"""
    return f'${amount:.2f}'


def clamp(value, min_val, max_val):
    """Return value clamped to [min_val, max_val]."""
    return max(min_val, min(max_val, value))
