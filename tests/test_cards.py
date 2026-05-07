from datetime import date, timedelta
import pytest
from app.models import Card
from app.extensions import db as _db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user_and_account(client, suffix='1'):
    u = client.post('/api/users/', json={'name': f'U{suffix}', 'email': f'u{suffix}@test.com'})
    user_id = u.get_json()['id']
    a = client.post('/api/accounts/', json={'user_id': user_id, 'type': 'checking'})
    return user_id, a.get_json()['id']


def issue_and_activate_card(client, account_id):
    r = client.post('/api/cards/', json={'account_id': account_id, 'daily_limit': 500.0})
    card_id = r.get_json()['id']
    client.post(f'/api/cards/{card_id}/activate')
    return card_id


# ---------------------------------------------------------------------------
# POST /api/cards/
# ---------------------------------------------------------------------------

def test_issue_card_success(client):
    _, account_id = make_user_and_account(client)
    resp = client.post('/api/cards/', json={'account_id': account_id, 'daily_limit': 1000.0})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['account_id'] == account_id
    assert data['daily_limit'] == pytest.approx(1000.0)
    assert data['is_active'] is False


def test_issue_card_generates_valid_luhn(client):
    from app.utils import validate_luhn
    _, account_id = make_user_and_account(client, suffix='4')
    resp = client.post('/api/cards/', json={'account_id': account_id})
    assert resp.status_code == 201
    data = resp.get_json()
    assert validate_luhn(data['number'])


# ---------------------------------------------------------------------------
# GET /api/cards/<id>
# ---------------------------------------------------------------------------

def test_get_card_success(client):
    _, account_id = make_user_and_account(client, suffix='5')
    r = client.post('/api/cards/', json={'account_id': account_id})
    card_id = r.get_json()['id']
    resp = client.get(f'/api/cards/{card_id}')
    assert resp.status_code == 200
    assert resp.get_json()['id'] == card_id


def test_get_card_not_found(client):
    resp = client.get('/api/cards/99999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/cards/account/<id>
# ---------------------------------------------------------------------------

def test_get_account_cards_success(client):
    _, account_id = make_user_and_account(client, suffix='6')
    client.post('/api/cards/', json={'account_id': account_id})
    client.post('/api/cards/', json={'account_id': account_id})
    resp = client.get(f'/api/cards/account/{account_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_get_account_cards_account_not_found(client):
    resp = client.get('/api/cards/account/99999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/cards/<id>/activate
# ---------------------------------------------------------------------------

def test_activate_card_success(client):
    _, account_id = make_user_and_account(client, suffix='7')
    r = client.post('/api/cards/', json={'account_id': account_id})
    card_id = r.get_json()['id']
    resp = client.post(f'/api/cards/{card_id}/activate')
    assert resp.status_code == 200
    assert resp.get_json()['is_active'] is True


def test_activate_card_stolen(client):
    _, account_id = make_user_and_account(client, suffix='8')
    r = client.post('/api/cards/', json={'account_id': account_id})
    card_id = r.get_json()['id']
    client.post(f'/api/cards/{card_id}/report-stolen')
    resp = client.post(f'/api/cards/{card_id}/activate')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_activate_card_not_found(client):
    resp = client.post('/api/cards/99999/activate')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/cards/<id>/limit
# ---------------------------------------------------------------------------

def test_set_daily_limit_success(client):
    _, account_id = make_user_and_account(client, suffix='10')
    r = client.post('/api/cards/', json={'account_id': account_id})
    card_id = r.get_json()['id']
    resp = client.post(f'/api/cards/{card_id}/limit', json={'limit': 2000.0})
    assert resp.status_code == 200
    assert resp.get_json()['daily_limit'] == pytest.approx(2000.0)


def test_set_daily_limit_zero(client):
    _, account_id = make_user_and_account(client, suffix='11')
    r = client.post('/api/cards/', json={'account_id': account_id})
    card_id = r.get_json()['id']
    resp = client.post(f'/api/cards/{card_id}/limit', json={'limit': 0})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_set_daily_limit_negative(client):
    _, account_id = make_user_and_account(client, suffix='12')
    r = client.post('/api/cards/', json={'account_id': account_id})
    card_id = r.get_json()['id']
    resp = client.post(f'/api/cards/{card_id}/limit', json={'limit': -100})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/cards/<id>/charge
# ---------------------------------------------------------------------------

def test_charge_card_success(client):
    _, account_id = make_user_and_account(client, suffix='13')
    card_id = issue_and_activate_card(client, account_id)
    resp = client.post(f'/api/cards/{card_id}/charge', json={'amount': 50.0})
    assert resp.status_code == 200
    assert resp.get_json()['daily_spent'] == pytest.approx(50.0)


def test_charge_card_zero_amount(client):
    _, account_id = make_user_and_account(client, suffix='14')
    card_id = issue_and_activate_card(client, account_id)
    resp = client.post(f'/api/cards/{card_id}/charge', json={'amount': 0})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_charge_card_stolen(client):
    _, account_id = make_user_and_account(client, suffix='15')
    r = client.post('/api/cards/', json={'account_id': account_id, 'daily_limit': 500.0})
    card_id = r.get_json()['id']
    client.post(f'/api/cards/{card_id}/report-stolen')
    resp = client.post(f'/api/cards/{card_id}/charge', json={'amount': 50.0})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_charge_card_inactive(client):
    _, account_id = make_user_and_account(client, suffix='16')
    r = client.post('/api/cards/', json={'account_id': account_id, 'daily_limit': 500.0})
    card_id = r.get_json()['id']
    # Card is not activated
    resp = client.post(f'/api/cards/{card_id}/charge', json={'amount': 50.0})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_charge_card_expired(client):
    _, account_id = make_user_and_account(client, suffix='17')
    card_id = issue_and_activate_card(client, account_id)
    # Directly set expiry_date to yesterday in the DB
    card_obj = Card.query.get(card_id)
    card_obj.expiry_date = date.today() - timedelta(days=1)
    _db.session.commit()
    resp = client.post(f'/api/cards/{card_id}/charge', json={'amount': 50.0})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_charge_card_exceeds_daily_limit(client):
    _, account_id = make_user_and_account(client, suffix='18')
    r = client.post('/api/cards/', json={'account_id': account_id, 'daily_limit': 10.0})
    card_id = r.get_json()['id']
    client.post(f'/api/cards/{card_id}/activate')
    resp = client.post(f'/api/cards/{card_id}/charge', json={'amount': 100.0})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/cards/<id>/report-stolen
# ---------------------------------------------------------------------------

def test_report_stolen_success(client):
    _, account_id = make_user_and_account(client, suffix='19')
    card_id = issue_and_activate_card(client, account_id)
    resp = client.post(f'/api/cards/{card_id}/report-stolen')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['is_stolen'] is True
    assert data['is_active'] is False


# ---------------------------------------------------------------------------
# POST /api/cards/<id>/renew
# ---------------------------------------------------------------------------

def test_renew_card_success(client):
    _, account_id = make_user_and_account(client, suffix='20')
    card_id = issue_and_activate_card(client, account_id)
    # Charge some amount first so daily_spent > 0
    client.post(f'/api/cards/{card_id}/charge', json={'amount': 100.0})
    resp = client.post(f'/api/cards/{card_id}/renew')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['daily_spent'] == pytest.approx(0.0)
    # Expiry date should be ~3 years from now
    expiry = date.fromisoformat(data['expiry_date'])
    assert expiry > date.today()
