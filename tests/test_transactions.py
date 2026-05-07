import datetime
import pytest
from app.models import Transaction, Account
from app.extensions import db as _db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user_and_account(client, email_suffix='1'):
    u = client.post('/api/users/', json={'name': f'U{email_suffix}', 'email': f'u{email_suffix}@t.com'})
    user_id = u.get_json()['id']
    a = client.post('/api/accounts/', json={'user_id': user_id, 'type': 'checking'})
    account_id = a.get_json()['id']
    return user_id, account_id


def fund_account(client, account_id, amount=500):
    client.post('/api/accounts/' + str(account_id) + '/deposit', json={'amount': amount})


# ---------------------------------------------------------------------------
# POST /api/transactions/transfer
# ---------------------------------------------------------------------------

def test_transfer_success(client):
    _, from_id = make_user_and_account(client, '1')
    _, to_id = make_user_and_account(client, '2')
    fund_account(client, from_id, 200)
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': to_id,
        'amount': 100,
        'description': 'test transfer',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['type'] == 'transfer'
    assert data['status'] == 'completed'
    assert data['amount'] == pytest.approx(100.0)
    assert data['description'] == 'test transfer'


def test_transfer_same_account(client):
    _, account_id = make_user_and_account(client, '1')
    fund_account(client, account_id, 200)
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': account_id,
        'to_account_id': account_id,
        'amount': 50,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_transfer_zero_amount(client):
    _, from_id = make_user_and_account(client, '1')
    _, to_id = make_user_and_account(client, '2')
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': to_id,
        'amount': 0,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_transfer_negative_amount(client):
    _, from_id = make_user_and_account(client, '1')
    _, to_id = make_user_and_account(client, '2')
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': to_id,
        'amount': -50,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_transfer_from_not_found(client):
    _, to_id = make_user_and_account(client, '2')
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': 99999,
        'to_account_id': to_id,
        'amount': 50,
    })
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


def test_transfer_to_not_found(client):
    _, from_id = make_user_and_account(client, '1')
    fund_account(client, from_id, 200)
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': 99999,
        'amount': 50,
    })
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


def test_transfer_source_frozen(client):
    _, from_id = make_user_and_account(client, '1')
    _, to_id = make_user_and_account(client, '2')
    fund_account(client, from_id, 200)
    client.post(f'/api/accounts/{from_id}/freeze')
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': to_id,
        'amount': 50,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_transfer_source_closed(client, db):
    _, from_id = make_user_and_account(client, '1')
    _, to_id = make_user_and_account(client, '2')
    # Set source account to closed directly via DB (bypass balance check)
    account = _db.session.get(Account, from_id)
    account.status = 'closed'
    _db.session.commit()
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': to_id,
        'amount': 50,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_transfer_dest_frozen(client):
    _, from_id = make_user_and_account(client, '1')
    _, to_id = make_user_and_account(client, '2')
    fund_account(client, from_id, 200)
    client.post(f'/api/accounts/{to_id}/freeze')
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': to_id,
        'amount': 50,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_transfer_dest_closed(client, db):
    _, from_id = make_user_and_account(client, '1')
    _, to_id = make_user_and_account(client, '2')
    fund_account(client, from_id, 200)
    # Set dest account to closed directly via DB
    account = _db.session.get(Account, to_id)
    account.status = 'closed'
    _db.session.commit()
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': to_id,
        'amount': 50,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_transfer_insufficient_funds(client):
    _, from_id = make_user_and_account(client, '1')
    _, to_id = make_user_and_account(client, '2')
    # from_id has balance 0, try to transfer 100
    resp = client.post('/api/transactions/transfer', json={
        'from_account_id': from_id,
        'to_account_id': to_id,
        'amount': 100,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/transactions/deposit
# ---------------------------------------------------------------------------

def test_deposit_success(client):
    _, account_id = make_user_and_account(client, '1')
    resp = client.post('/api/transactions/deposit', json={
        'account_id': account_id,
        'amount': 250,
        'description': 'salary',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['type'] == 'deposit'
    assert data['status'] == 'completed'
    assert data['amount'] == pytest.approx(250.0)
    assert data['description'] == 'salary'


def test_deposit_zero(client):
    _, account_id = make_user_and_account(client, '1')
    resp = client.post('/api/transactions/deposit', json={
        'account_id': account_id,
        'amount': 0,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_deposit_frozen(client):
    _, account_id = make_user_and_account(client, '1')
    client.post(f'/api/accounts/{account_id}/freeze')
    resp = client.post('/api/transactions/deposit', json={
        'account_id': account_id,
        'amount': 100,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_deposit_closed(client, db):
    _, account_id = make_user_and_account(client, '1')
    account = _db.session.get(Account, account_id)
    account.status = 'closed'
    _db.session.commit()
    resp = client.post('/api/transactions/deposit', json={
        'account_id': account_id,
        'amount': 100,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/transactions/withdraw
# ---------------------------------------------------------------------------

def test_withdraw_success(client):
    _, account_id = make_user_and_account(client, '1')
    fund_account(client, account_id, 300)
    resp = client.post('/api/transactions/withdraw', json={
        'account_id': account_id,
        'amount': 100,
        'description': 'atm',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['type'] == 'withdrawal'
    assert data['status'] == 'completed'
    assert data['amount'] == pytest.approx(100.0)
    assert data['description'] == 'atm'


def test_withdraw_zero(client):
    _, account_id = make_user_and_account(client, '1')
    resp = client.post('/api/transactions/withdraw', json={
        'account_id': account_id,
        'amount': 0,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_frozen(client):
    _, account_id = make_user_and_account(client, '1')
    fund_account(client, account_id, 200)
    client.post(f'/api/accounts/{account_id}/freeze')
    resp = client.post('/api/transactions/withdraw', json={
        'account_id': account_id,
        'amount': 50,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_closed(client, db):
    _, account_id = make_user_and_account(client, '1')
    account = _db.session.get(Account, account_id)
    account.status = 'closed'
    account.balance = 200
    _db.session.commit()
    resp = client.post('/api/transactions/withdraw', json={
        'account_id': account_id,
        'amount': 50,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_withdraw_insufficient(client):
    _, account_id = make_user_and_account(client, '1')
    # balance is 0, try to withdraw
    resp = client.post('/api/transactions/withdraw', json={
        'account_id': account_id,
        'amount': 100,
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/transactions/<id>
# ---------------------------------------------------------------------------

def test_get_transaction_success(client):
    _, account_id = make_user_and_account(client, '1')
    deposit_resp = client.post('/api/transactions/deposit', json={
        'account_id': account_id,
        'amount': 100,
    })
    tx_id = deposit_resp.get_json()['id']
    resp = client.get(f'/api/transactions/{tx_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == tx_id
    assert data['type'] == 'deposit'


def test_get_transaction_not_found(client):
    resp = client.get('/api/transactions/99999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/transactions/account/<id>
# ---------------------------------------------------------------------------

def test_get_account_transactions_all(client):
    _, account_id = make_user_and_account(client, '1')
    fund_account(client, account_id, 500)
    client.post('/api/transactions/withdraw', json={'account_id': account_id, 'amount': 100})
    resp = client.get(f'/api/transactions/account/{account_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    # deposit via fund_account + withdrawal
    assert len(data) >= 2


def test_get_account_transactions_by_type(client):
    _, account_id = make_user_and_account(client, '1')
    _, other_id = make_user_and_account(client, '2')
    fund_account(client, account_id, 500)
    # Create a transfer so there's a mix of types
    client.post('/api/transactions/transfer', json={
        'from_account_id': account_id,
        'to_account_id': other_id,
        'amount': 50,
    })
    resp = client.get(f'/api/transactions/account/{account_id}?type=deposit')
    assert resp.status_code == 200
    data = resp.get_json()
    assert all(tx['type'] == 'deposit' for tx in data)
    assert len(data) >= 1


def test_get_account_transactions_from_date(client):
    _, account_id = make_user_and_account(client, '1')
    fund_account(client, account_id, 100)
    resp = client.get(f'/api/transactions/account/{account_id}?from=2020-01-01')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1


def test_get_account_transactions_to_date(client):
    _, account_id = make_user_and_account(client, '1')
    fund_account(client, account_id, 100)
    resp = client.get(f'/api/transactions/account/{account_id}?to=2030-01-01')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1


def test_get_account_transactions_account_not_found(client):
    resp = client.get('/api/transactions/account/99999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/transactions/<id>/cancel
# ---------------------------------------------------------------------------

def test_cancel_pending_transaction(client, db):
    _, account_id = make_user_and_account(client, '1')
    # Create a Transaction directly in DB with status='pending'
    tx = Transaction(
        to_account_id=account_id,
        amount=50,
        type='deposit',
        status='pending',
    )
    _db.session.add(tx)
    _db.session.commit()
    tx_id = tx.id
    resp = client.post(f'/api/transactions/{tx_id}/cancel')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'failed'


def test_cancel_completed_transaction(client):
    _, account_id = make_user_and_account(client, '1')
    deposit_resp = client.post('/api/transactions/deposit', json={
        'account_id': account_id,
        'amount': 100,
    })
    tx_id = deposit_resp.get_json()['id']
    resp = client.post(f'/api/transactions/{tx_id}/cancel')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_cancel_not_found(client):
    resp = client.post('/api/transactions/99999/cancel')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/transactions/batch-transfer
# ---------------------------------------------------------------------------

def test_batch_transfer_success(client):
    _, from_id = make_user_and_account(client, '1')
    _, to_id1 = make_user_and_account(client, '2')
    _, to_id2 = make_user_and_account(client, '3')
    fund_account(client, from_id, 1000)
    resp = client.post('/api/transactions/batch-transfer', json={
        'from_account_id': from_id,
        'recipients': [
            {'account_id': to_id1, 'amount': 100},
            {'account_id': to_id2, 'amount': 200},
        ],
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert len(data) == 2
    assert all(tx['type'] == 'transfer' for tx in data)


def test_batch_transfer_partial_failure(client):
    _, from_id = make_user_and_account(client, '1')
    _, to_id1 = make_user_and_account(client, '2')
    _, to_id2 = make_user_and_account(client, '3')
    fund_account(client, from_id, 1000)
    # Freeze the second recipient so the second transfer fails
    client.post(f'/api/accounts/{to_id2}/freeze')
    resp = client.post('/api/transactions/batch-transfer', json={
        'from_account_id': from_id,
        'recipients': [
            {'account_id': to_id1, 'amount': 100},
            {'account_id': to_id2, 'amount': 200},
        ],
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/transactions/stats/daily
# ---------------------------------------------------------------------------

def test_daily_stats_empty(client):
    resp = client.get('/api/transactions/stats/daily?date=2020-01-01')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] == 0
    assert data['total_amount'] == 0.0
    assert data['date'] == '2020-01-01'


def test_daily_stats_with_transactions(client, db):
    _, account_id = make_user_and_account(client, '1')
    # Insert a transaction with an explicit created_at so the date is predictable
    tx = Transaction(
        to_account_id=account_id,
        amount=150,
        type='deposit',
        status='completed',
        created_at=datetime.datetime(2025, 6, 15, 12, 0, 0),
    )
    _db.session.add(tx)
    _db.session.commit()
    resp = client.get('/api/transactions/stats/daily?date=2025-06-15')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] >= 1
    assert data['total_amount'] >= 150.0
    assert data['date'] == '2025-06-15'


# ---------------------------------------------------------------------------
# GET /api/transactions/stats/monthly
# ---------------------------------------------------------------------------

def test_monthly_stats_empty(client):
    resp = client.get('/api/transactions/stats/monthly?year=2019&month=6')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] == 0
    assert data['by_type'] == {}
    assert data['year'] == 2019
    assert data['month'] == 6


def test_monthly_stats_with_transactions(client, db):
    _, account_id = make_user_and_account(client, '1')
    # Insert two deposits in a fixed month to exercise the by_type accumulation branch
    # (second iteration hits the `tx.type already in by_type` branch)
    for amount in (100, 200):
        tx = Transaction(
            to_account_id=account_id,
            amount=amount,
            type='deposit',
            status='completed',
            created_at=datetime.datetime(2025, 6, 15, 12, 0, 0),
        )
        _db.session.add(tx)
    _db.session.commit()
    resp = client.get('/api/transactions/stats/monthly?year=2025&month=6')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] >= 2
    assert 'deposit' in data['by_type']
    assert data['by_type']['deposit']['count'] >= 2
    assert data['by_type']['deposit']['total'] >= 300.0


def test_monthly_stats_december(client):
    # Exercise the month==12 branch in get_monthly_stats
    resp = client.get('/api/transactions/stats/monthly?year=2023&month=12')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['year'] == 2023
    assert data['month'] == 12
    assert data['count'] == 0
