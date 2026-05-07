from datetime import date, datetime, timedelta
from app.utils import (
    validate_email,
    generate_card_number,
    validate_luhn,
    calculate_monthly_payment,
    calculate_loan_schedule,
    hash_cvv,
    verify_cvv,
    is_card_expired,
    paginate,
    parse_date_range,
    format_currency,
    clamp,
)
from app.models import User


# ---------------------------------------------------------------------------
# validate_email
# ---------------------------------------------------------------------------

def test_validate_email_valid():
    assert validate_email('user@example.com') is True


def test_validate_email_no_at():
    assert validate_email('userexample.com') is False


def test_validate_email_no_tld():
    assert validate_email('user@example') is False


def test_validate_email_empty():
    assert validate_email('') is False


def test_validate_email_subdomain():
    assert validate_email('user@mail.example.co.uk') is True


def test_validate_email_plus_local():
    assert validate_email('user+tag@example.com') is True


# ---------------------------------------------------------------------------
# generate_card_number
# ---------------------------------------------------------------------------

def test_generate_card_number_length():
    number = generate_card_number()
    assert len(number) == 16
    assert number.isdigit()


def test_generate_card_number_luhn_valid():
    number = generate_card_number()
    assert validate_luhn(number) is True


# ---------------------------------------------------------------------------
# validate_luhn
# ---------------------------------------------------------------------------

def test_validate_luhn_valid_number():
    # Known Luhn-valid Visa test number
    assert validate_luhn('4532015112830366') is True


def test_validate_luhn_invalid_number():
    assert validate_luhn('1234567890123456') is False


def test_validate_luhn_non_digit_string():
    # No digit characters → digits list is empty → returns False
    assert validate_luhn('abcdefgh') is False


def test_validate_luhn_double_greater_than_nine():
    # 4532015112830366: contains digits that when doubled exceed 9
    # (e.g. the digit 9 at position 0 from right in the doubled positions
    # doubles to 18 → 18-9=9). Confirmed valid and exercises the d>9 branch.
    assert validate_luhn('4532015112830366') is True

    # Construct a number explicitly containing 6 in a doubled position:
    # 6*2=12 > 9 → 12-9=3. Use another known-valid number that has such digits.
    assert validate_luhn('4111111111111111') is True


# ---------------------------------------------------------------------------
# calculate_monthly_payment
# ---------------------------------------------------------------------------

def test_calculate_monthly_payment_zero_rate():
    # $1200 over 12 months at 0% → $100.00 each
    result = calculate_monthly_payment(1200.0, 0.0, 12)
    assert result == 100.00


def test_calculate_monthly_payment_nonzero_rate():
    # $10000, 12% annual, 12 months → known annuity payment ≈ $888.49
    result = calculate_monthly_payment(10000.0, 0.12, 12)
    assert result == 888.49


# ---------------------------------------------------------------------------
# calculate_loan_schedule
# ---------------------------------------------------------------------------

def test_calculate_loan_schedule_nonzero_rate():
    schedule = calculate_loan_schedule(10000.0, 0.12, 12)
    assert len(schedule) == 12
    # First entry
    first = schedule[0]
    assert first['month'] == 1
    assert first['payment'] == 888.49
    assert first['interest'] == round(10000.0 * 0.12 / 12, 2)  # 100.0
    assert first['principal'] == round(888.49 - 100.0, 2)       # 788.49
    # Last entry must have remaining == 0
    last = schedule[-1]
    assert last['month'] == 12
    assert last['remaining'] == 0.0


def test_calculate_loan_schedule_zero_rate():
    # Zero rate: no interest each month
    schedule = calculate_loan_schedule(1200.0, 0.0, 12)
    assert len(schedule) == 12
    for entry in schedule:
        assert entry['interest'] == 0.0
    assert schedule[-1]['remaining'] == 0.0


# ---------------------------------------------------------------------------
# hash_cvv
# ---------------------------------------------------------------------------

def test_hash_cvv_returns_64_char_hex():
    result = hash_cvv('123')
    assert len(result) == 64
    assert all(c in '0123456789abcdef' for c in result)


# ---------------------------------------------------------------------------
# verify_cvv
# ---------------------------------------------------------------------------

def test_verify_cvv_correct():
    hashed = hash_cvv('456')
    assert verify_cvv('456', hashed) is True


def test_verify_cvv_wrong():
    hashed = hash_cvv('456')
    assert verify_cvv('789', hashed) is False


# ---------------------------------------------------------------------------
# is_card_expired
# ---------------------------------------------------------------------------

def test_is_card_expired_past_date():
    past = date.today() - timedelta(days=1)
    assert is_card_expired(past) is True


def test_is_card_expired_future_date():
    future = date.today() + timedelta(days=1)
    assert is_card_expired(future) is False


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------

def test_paginate_empty(app):
    with app.app_context():
        result = paginate(User.query, 1, 10)
        assert result['total'] == 0
        assert result['pages'] == 1  # max(1, ...) branch — zero items → pages=1
        assert result['items'] == []
        assert result['page'] == 1


def test_paginate_with_data(app, db):
    with app.app_context():
        for i in range(5):
            u = User(name=f'User{i}', email=f'user{i}@test.com')
            db.session.add(u)
        db.session.commit()

        # Page 1: 3 items out of 5
        result = paginate(User.query, 1, 3)
        assert result['total'] == 5
        assert result['pages'] == 2
        assert len(result['items']) == 3
        assert result['page'] == 1

        # Page 2: remaining 2 items (tests offset logic)
        result2 = paginate(User.query, 2, 3)
        assert len(result2['items']) == 2
        assert result2['page'] == 2


# ---------------------------------------------------------------------------
# parse_date_range
# ---------------------------------------------------------------------------

def test_parse_date_range_both_provided():
    from_dt, to_dt = parse_date_range('2024-01-01', '2024-12-31')
    assert from_dt == datetime(2024, 1, 1)
    assert to_dt == datetime(2024, 12, 31)


def test_parse_date_range_both_none():
    from_dt, to_dt = parse_date_range(None, None)
    assert from_dt is None
    assert to_dt is None


def test_parse_date_range_from_only():
    from_dt, to_dt = parse_date_range('2024-06-15', None)
    assert from_dt == datetime(2024, 6, 15)
    assert to_dt is None


def test_parse_date_range_to_only():
    from_dt, to_dt = parse_date_range(None, '2024-09-30')
    assert from_dt is None
    assert to_dt == datetime(2024, 9, 30)


# ---------------------------------------------------------------------------
# format_currency
# ---------------------------------------------------------------------------

def test_format_currency_positive():
    assert format_currency(1234.56) == '$1234.56'


def test_format_currency_zero():
    assert format_currency(0.0) == '$0.00'


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------

def test_clamp_within_range():
    assert clamp(5, 1, 10) == 5


def test_clamp_below_min():
    assert clamp(-3, 0, 10) == 0


def test_clamp_above_max():
    assert clamp(15, 0, 10) == 10
