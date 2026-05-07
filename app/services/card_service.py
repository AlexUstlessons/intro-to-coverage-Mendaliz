import random
import string
from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models import Card
from app.exceptions import (
    NotFoundError, CardExpiredError, CardInactiveError, CardStolenError,
    DailyLimitExceededError, InvalidAmountError,
)
from app.utils import generate_card_number, hash_cvv, is_card_expired
from app.services.account_service import get_account


def _generate_cvv() -> str:
    return ''.join(random.choices(string.digits, k=3))


def issue_card(account_id: int, daily_limit: float = 1000.0) -> Card:
    get_account(account_id)  # raises NotFoundError if not found
    if daily_limit <= 0:
        raise InvalidAmountError('Daily limit must be positive')
    number = generate_card_number()
    cvv = _generate_cvv()
    expiry = date.today().replace(year=date.today().year + 3)
    card = Card(
        account_id=account_id,
        number=number,
        cvv_hash=hash_cvv(cvv),
        expiry_date=expiry,
        is_active=False,
        daily_limit=Decimal(str(daily_limit)),
    )
    db.session.add(card)
    db.session.commit()
    return card


def get_card(card_id: int) -> Card:
    card = Card.query.get(card_id)
    if not card:
        raise NotFoundError(f'Card {card_id} not found')
    return card


def get_account_cards(account_id: int) -> list:
    get_account(account_id)
    return Card.query.filter_by(account_id=account_id).all()


def activate_card(card_id: int) -> Card:
    card = get_card(card_id)
    if card.is_stolen:
        raise CardStolenError('Cannot activate a stolen card')
    card.is_active = True
    db.session.commit()
    return card


def deactivate_card(card_id: int) -> Card:
    card = get_card(card_id)
    card.is_active = False
    db.session.commit()
    return card


def set_daily_limit(card_id: int, limit: float) -> Card:
    card = get_card(card_id)
    if limit <= 0:
        raise InvalidAmountError('Daily limit must be positive')
    card.daily_limit = Decimal(str(limit))
    db.session.commit()
    return card


def charge_card(card_id: int, amount: float) -> Card:
    card = get_card(card_id)
    amount = Decimal(str(amount))
    if amount <= 0:
        raise InvalidAmountError('Charge amount must be positive')
    if card.is_stolen:
        raise CardStolenError('Card has been reported stolen')
    if not card.is_active:
        raise CardInactiveError('Card is not active')
    if is_card_expired(card.expiry_date):
        raise CardExpiredError('Card has expired')
    if card.daily_spent + amount > card.daily_limit:
        raise DailyLimitExceededError('Daily limit would be exceeded')
    card.daily_spent += amount
    db.session.commit()
    return card


def report_stolen(card_id: int) -> Card:
    card = get_card(card_id)
    card.is_stolen = True
    card.is_active = False
    db.session.commit()
    return card


def renew_card(card_id: int) -> Card:
    card = get_card(card_id)
    card.expiry_date = date.today().replace(year=date.today().year + 3)
    cvv = _generate_cvv()
    card.cvv_hash = hash_cvv(cvv)
    card.daily_spent = Decimal('0.00')
    db.session.commit()
    return card
