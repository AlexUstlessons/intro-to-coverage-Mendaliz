import pytest
from app.models import Account
from app.extensions import db as _db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(client, name='Alice', email='alice@test.com'):
    resp = client.post('/api/users/', json={'name': name, 'email': email})
    return resp.get_json()['id']


def make_account(client, user_id, account_type='checking'):
    resp = client.post('/api/accounts/', json={'user_id': user_id, 'type': account_type})
    return resp.get_json()['id']


# ---------------------------------------------------------------------------
# POST /api/accounts/
# ---------------------------------------------------------------------------

def test_create_account_checking(client):
    user_id = make_user(client)
    resp = client.post('/api/accounts/', json={'user_id': user_id, 'type': 'checking'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['type'] == 'checking'
    assert data['status'] == 'active'
    assert data['balance'] == 0.0


def test_create_account_savings(client):
    user_id = make_user(client)
    resp = client.post('/api/accounts/', json={'user_id': user_id, 'type': 'savings'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['type'] == 'savings'


def test_create_account_investment(client):
    user_id = make_user(client)
    resp = client.post('/api/accounts/', json={'user_id': user_id, 'type': 'investment'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['type'] == 'investment'


def test_create_account_invalid_type(client):
    user_id = make_user(client)
    resp = client.post('/api/accounts/', json={'user_id': user_id, 'type': 'crypto'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_create_account_user_not_found(client):
    resp = client.post('/api/accounts/', json={'user_id': 99999, 'type': 'checking'})
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/accounts/user/<id>
# ---------------------------------------------------------------------------

def test_get_user_accounts_success(client):
    user_id = make_user(client)
    make_account(client, user_id, 'checking')
    make_account(client, user_id, 'savings')
    resp = client.get(f'/api/accounts/user/{user_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_get_user_accounts_user_not_found(client):
    resp = client.get('/api/accounts/user/99999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/accounts/<id>
# ---------------------------------------------------------------------------

def test_get_account_success(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    resp = client.get(f'/api/accounts/{account_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == account_id


def test_get_account_not_found(client):
    resp = client.get('/api/accounts/99999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/accounts/<id>/deposit
# ---------------------------------------------------------------------------

def test_deposit_success(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    resp = client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 100.00})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['balance'] == pytest.approx(100.00)


def test_deposit_zero_amount(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    resp = client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 0})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_deposit_negative_amount(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    resp = client.post(f'/api/accounts/{account_id}/deposit', json={'amount': -50})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_deposit_frozen_account(client, db):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    # Freeze the account
    client.post(f'/api/accounts/{account_id}/freeze')
    resp = client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 100})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_deposit_closed_account(client, db):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    # Close account (balance is 0)
    client.post(f'/api/accounts/{account_id}/close')
    resp = client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 100})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_deposit_exceeds_daily_limit(client, db):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    # Default daily_deposit_limit is 10000; deposit more than that
    resp = client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 10001})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/accounts/<id>/withdraw
# ---------------------------------------------------------------------------

def test_withdraw_success(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 500})
    resp = client.post(f'/api/accounts/{account_id}/withdraw', json={'amount': 200})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['balance'] == pytest.approx(300.00)


def test_withdraw_zero_amount(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    resp = client.post(f'/api/accounts/{account_id}/withdraw', json={'amount': 0})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_negative_amount(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    resp = client.post(f'/api/accounts/{account_id}/withdraw', json={'amount': -10})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_frozen_account(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 100})
    client.post(f'/api/accounts/{account_id}/freeze')
    resp = client.post(f'/api/accounts/{account_id}/withdraw', json={'amount': 50})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_closed_account(client, db):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    # Directly set status to closed with balance so we can hit the closed check
    # (normally you can't close an account with balance; set via DB)
    account = _db.session.get(Account, account_id)
    account.status = 'closed'
    account.balance = 100
    _db.session.commit()
    resp = client.post(f'/api/accounts/{account_id}/withdraw', json={'amount': 50})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_savings_minimum_balance(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id, 'savings')
    # Deposit exactly $20 (above minimum of $10)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 20})
    # Withdraw $15 → would leave $5, which is below $10 minimum
    resp = client.post(f'/api/accounts/{account_id}/withdraw', json={'amount': 15})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_insufficient_no_overdraft(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    # Balance is 0, overdraft disabled by default
    resp = client.post(f'/api/accounts/{account_id}/withdraw', json={'amount': 100})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_with_overdraft_enabled(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    # Enable overdraft
    client.post(f'/api/accounts/{account_id}/overdraft', json={'enabled': True})
    # Withdraw more than balance (0 by default) → success, goes negative
    resp = client.post(f'/api/accounts/{account_id}/withdraw', json={'amount': 50})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['balance'] == pytest.approx(-50.00)


# ---------------------------------------------------------------------------
# POST /api/accounts/<id>/freeze
# ---------------------------------------------------------------------------

def test_freeze_account_success(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    resp = client.post(f'/api/accounts/{account_id}/freeze')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'frozen'


def test_freeze_account_already_frozen(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/freeze')
    resp = client.post(f'/api/accounts/{account_id}/freeze')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_freeze_account_closed(client, db):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/close')
    resp = client.post(f'/api/accounts/{account_id}/freeze')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/accounts/<id>/unfreeze
# ---------------------------------------------------------------------------

def test_unfreeze_account_success(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/freeze')
    resp = client.post(f'/api/accounts/{account_id}/unfreeze')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'active'


def test_unfreeze_account_not_frozen(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    # Account is active, not frozen
    resp = client.post(f'/api/accounts/{account_id}/unfreeze')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/accounts/<id>/close
# ---------------------------------------------------------------------------

def test_close_account_success(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    # Balance is 0 by default → can close
    resp = client.post(f'/api/accounts/{account_id}/close')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'closed'


def test_close_account_not_empty(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 100})
    resp = client.post(f'/api/accounts/{account_id}/close')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_close_account_already_closed(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/close')
    resp = client.post(f'/api/accounts/{account_id}/close')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/accounts/<id>/overdraft
# ---------------------------------------------------------------------------

def test_set_overdraft_enabled_checking(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id, 'checking')
    resp = client.post(f'/api/accounts/{account_id}/overdraft', json={'enabled': True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['overdraft_enabled'] is True


def test_set_overdraft_disabled(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id, 'checking')
    # First enable then disable
    client.post(f'/api/accounts/{account_id}/overdraft', json={'enabled': True})
    resp = client.post(f'/api/accounts/{account_id}/overdraft', json={'enabled': False})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['overdraft_enabled'] is False


def test_set_overdraft_investment(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id, 'investment')
    resp = client.post(f'/api/accounts/{account_id}/overdraft', json={'enabled': True})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/accounts/<id>/history
# ---------------------------------------------------------------------------

def test_get_balance_history_empty(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    resp = client.get(f'/api/accounts/{account_id}/history')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == []


def test_get_balance_history_with_data(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 100})
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 50})
    resp = client.get(f'/api/accounts/{account_id}/history')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_get_balance_history_not_found(client):
    resp = client.get('/api/accounts/99999/history')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/accounts/<id>/statement
# ---------------------------------------------------------------------------

def test_get_statement_no_filters(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 200})
    resp = client.get(f'/api/accounts/{account_id}/statement')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1


def test_get_statement_with_from_date(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 200})
    # Use a past from_date so transaction is included
    resp = client.get(f'/api/accounts/{account_id}/statement?from=2020-01-01')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1


def test_get_statement_with_to_date(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 200})
    # Use a future to_date so transaction is included
    resp = client.get(f'/api/accounts/{account_id}/statement?to=2030-01-01')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1


def test_get_statement_with_both_dates(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id)
    client.post(f'/api/accounts/{account_id}/deposit', json={'amount': 200})
    resp = client.get(f'/api/accounts/{account_id}/statement?from=2020-01-01&to=2030-01-01')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1


# ---------------------------------------------------------------------------
# POST /api/accounts/bulk-deposit
# ---------------------------------------------------------------------------

def test_bulk_deposit_success(client):
    user_id = make_user(client)
    account_id1 = make_account(client, user_id, 'checking')
    account_id2 = make_account(client, user_id, 'savings')
    resp = client.post('/api/accounts/bulk-deposit', json={
        'deposits': [
            {'account_id': account_id1, 'amount': 100},
            {'account_id': account_id2, 'amount': 50},
        ]
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    balances = {a['id']: a['balance'] for a in data}
    assert balances[account_id1] == pytest.approx(100.0)
    assert balances[account_id2] == pytest.approx(50.0)


def test_bulk_deposit_one_fails(client):
    user_id = make_user(client)
    account_id = make_account(client, user_id, 'checking')
    # Second entry has an invalid amount (0) → should raise InvalidAmountError
    resp = client.post('/api/accounts/bulk-deposit', json={
        'deposits': [
            {'account_id': account_id, 'amount': 100},
            {'account_id': account_id, 'amount': 0},
        ]
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()
