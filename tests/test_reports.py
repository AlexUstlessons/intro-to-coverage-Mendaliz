import pytest
from datetime import datetime, timedelta
from app.models import AuditLog, Loan, Account


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(client, suffix='1'):
    resp = client.post('/api/users/', json={'name': f'U{suffix}', 'email': f'u{suffix}@t.com'})
    return resp.get_json()['id']


def make_account_and_deposit(client, user_id, amount=500, acc_type='checking'):
    a = client.post('/api/accounts/', json={'user_id': user_id, 'type': acc_type})
    acc_id = a.get_json()['id']
    if amount:
        client.post(f'/api/accounts/{acc_id}/deposit', json={'amount': amount})
    return acc_id


# ---------------------------------------------------------------------------
# GET /api/reports/balance/<user_id>
# ---------------------------------------------------------------------------

def test_get_user_balance_no_accounts(client):
    user_id = make_user(client, suffix='bna')
    resp = client.get(f'/api/reports/balance/{user_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['user_id'] == user_id
    assert data['total_balance'] == 0.0
    assert data['account_count'] == 0
    assert data['accounts'] == []


def test_get_user_balance_with_accounts(client):
    user_id = make_user(client, suffix='bwa')
    make_account_and_deposit(client, user_id, amount=300)
    make_account_and_deposit(client, user_id, amount=200)
    resp = client.get(f'/api/reports/balance/{user_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['account_count'] == 2
    assert data['total_balance'] == pytest.approx(500.0)
    assert len(data['accounts']) == 2


def test_get_user_balance_user_not_found(client):
    resp = client.get('/api/reports/balance/9999')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/reports/transactions/summary
# ---------------------------------------------------------------------------

def test_transaction_summary_empty(client):
    resp = client.get('/api/reports/transactions/summary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total_transactions'] == 0
    assert data['by_type'] == {}


def test_transaction_summary_with_data(client):
    # Create two deposits for the same type to exercise the accumulation (else) branch,
    # plus a withdrawal to cover a second type key being added.
    user_id = make_user(client, suffix='tsd')
    acc_id = make_account_and_deposit(client, user_id, amount=500)
    # Second deposit — same type, so 'deposit' key already exists → else branch hit
    client.post(f'/api/accounts/{acc_id}/deposit', json={'amount': 200})
    # Withdrawal — new type key
    client.post(f'/api/accounts/{acc_id}/withdraw', json={'amount': 50})
    resp = client.get('/api/reports/transactions/summary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total_transactions'] >= 3
    by_type = data['by_type']
    assert 'deposit' in by_type
    assert by_type['deposit']['count'] >= 2
    assert 'withdrawal' in by_type


# ---------------------------------------------------------------------------
# GET /api/reports/top-accounts
# ---------------------------------------------------------------------------

def test_top_accounts_empty(client):
    resp = client.get('/api/reports/top-accounts')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_top_accounts_ordered(client):
    user_id = make_user(client, suffix='tao')
    make_account_and_deposit(client, user_id, amount=100)
    make_account_and_deposit(client, user_id, amount=900)
    resp = client.get('/api/reports/top-accounts')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    # Highest balance should come first
    assert data[0]['balance'] >= data[1]['balance']


def test_top_accounts_custom_limit(client):
    user_id = make_user(client, suffix='tacl')
    for i in range(5):
        make_account_and_deposit(client, user_id, amount=100 * (i + 1))
    resp = client.get('/api/reports/top-accounts?limit=3')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3


# ---------------------------------------------------------------------------
# GET /api/reports/revenue
# ---------------------------------------------------------------------------

def test_revenue_no_loans(client):
    resp = client.get('/api/reports/revenue')
    assert resp.status_code == 200
    assert resp.get_json()['total_interest_revenue'] == 0.0


def test_revenue_with_loans(client):
    user_id = make_user(client, suffix='rwl')
    make_account_and_deposit(client, user_id, amount=10000)
    # Apply and approve a loan with non-zero interest
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12,
    })
    loan_id = r.get_json()['id']
    client.post(f'/api/loans/{loan_id}/approve')
    resp = client.get('/api/reports/revenue')
    assert resp.status_code == 200
    assert resp.get_json()['total_interest_revenue'] > 0.0


# ---------------------------------------------------------------------------
# GET /api/reports/monthly/<user_id>
# ---------------------------------------------------------------------------

def test_monthly_report_no_transactions(client):
    user_id = make_user(client, suffix='mrnt')
    make_account_and_deposit(client, user_id, amount=0)
    now = datetime.utcnow()
    resp = client.get(f'/api/reports/monthly/{user_id}?month={now.month}&year={now.year}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['transaction_count'] == 0
    assert data['total_in'] == 0.0
    assert data['total_out'] == 0.0


def test_monthly_report_with_transactions(client):
    """Covers both total_in and total_out branches."""
    now = datetime.utcnow()
    user_id = make_user(client, suffix='mrwt')
    acc_id = make_account_and_deposit(client, user_id, amount=1000)

    user2_id = make_user(client, suffix='mrwt2')
    acc2_id = make_account_and_deposit(client, user2_id, amount=200)

    # Transfer from acc_id to acc2_id → outflow for user_id
    client.post('/api/transactions/transfer', json={
        'from_account_id': acc_id,
        'to_account_id': acc2_id,
        'amount': 100,
    })

    resp = client.get(f'/api/reports/monthly/{user_id}?month={now.month}&year={now.year}')
    assert resp.status_code == 200
    data = resp.get_json()
    # deposit creates total_in, transfer creates total_out
    assert data['total_in'] > 0
    assert data['total_out'] > 0


def test_monthly_report_no_accounts(client):
    """User with no accounts → account_ids is empty → txs = [] (empty list branch)."""
    user_id = make_user(client, suffix='mrna')
    now = datetime.utcnow()
    resp = client.get(f'/api/reports/monthly/{user_id}?month={now.month}&year={now.year}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['transaction_count'] == 0


def test_monthly_report_december(client):
    """month=12 exercises the year+1 rollover branch."""
    user_id = make_user(client, suffix='mrdec')
    resp = client.get(f'/api/reports/monthly/{user_id}?month=12&year=2023')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['month'] == 12
    assert data['year'] == 2023


def test_monthly_report_user_not_found(client):
    resp = client.get('/api/reports/monthly/9999?month=1&year=2024')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/reports/risk
# ---------------------------------------------------------------------------

def test_risk_analysis_no_risk(client):
    resp = client.get('/api/reports/risk')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['overdraft_count'] == 0
    assert data['overdue_loan_count'] == 0
    assert data['overdraft_accounts'] == []
    assert data['overdue_loans'] == []


def test_risk_analysis_with_overdraft(client, db):
    user_id = make_user(client, suffix='rawo')
    acc_id = make_account_and_deposit(client, user_id, amount=500)
    # Enable overdraft directly via model
    acc = Account.query.get(acc_id)
    acc.overdraft_enabled = True
    db.session.commit()
    resp = client.get('/api/reports/risk')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['overdraft_count'] == 1
    assert data['overdraft_accounts'][0]['id'] == acc_id


def test_risk_analysis_with_overdue_loan(client, db):
    """Approved loan with backdated created_at → appears in overdue_loans."""
    user_id = make_user(client, suffix='rawol')
    make_account_and_deposit(client, user_id, amount=10000)
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12,
    })
    loan_id = r.get_json()['id']
    client.post(f'/api/loans/{loan_id}/approve')
    # Backdate so it's overdue
    loan_obj = Loan.query.get(loan_id)
    loan_obj.created_at = datetime.utcnow() - timedelta(days=400)
    db.session.commit()
    resp = client.get('/api/reports/risk')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['overdue_loan_count'] == 1
    assert data['overdue_loans'][0]['id'] == loan_id


def test_risk_analysis_approved_not_overdue(client):
    """Approved loan with recent created_at → NOT overdue; exercises the 'if due < now' False branch."""
    user_id = make_user(client, suffix='ranod')
    make_account_and_deposit(client, user_id, amount=10000)
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12,
    })
    loan_id = r.get_json()['id']
    client.post(f'/api/loans/{loan_id}/approve')
    # created_at is now (default), term=12 months → due is ~1 year from now → NOT overdue
    resp = client.get('/api/reports/risk')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['overdue_loan_count'] == 0


# ---------------------------------------------------------------------------
# GET /api/reports/audit
# ---------------------------------------------------------------------------

def _make_audit_log(db, user_id, action='login'):
    log = AuditLog(user_id=user_id, action=action, entity_type='user', entity_id=user_id)
    db.session.add(log)
    db.session.commit()
    return log.id


def test_audit_log_empty(client):
    resp = client.get('/api/reports/audit')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_audit_log_no_filters(client, db):
    """Both user_id and action are None → neither if-branch taken."""
    user_id = make_user(client, suffix='alnf')
    _make_audit_log(db, user_id, action='login')
    resp = client.get('/api/reports/audit')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_audit_log_with_user_filter(client, db):
    user_id = make_user(client, suffix='aluf')
    other_user_id = make_user(client, suffix='aluf2')
    _make_audit_log(db, user_id, action='login')
    _make_audit_log(db, other_user_id, action='login')
    resp = client.get(f'/api/reports/audit?user_id={user_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['user_id'] == user_id


def test_audit_log_with_action_filter(client, db):
    user_id = make_user(client, suffix='alaf')
    _make_audit_log(db, user_id, action='login')
    _make_audit_log(db, user_id, action='logout')
    resp = client.get('/api/reports/audit?action=login')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['action'] == 'login'


# ---------------------------------------------------------------------------
# GET /api/reports/daily-volumes
# ---------------------------------------------------------------------------

def test_daily_volumes_empty(client):
    resp = client.get('/api/reports/daily-volumes')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_daily_volumes_no_filters(client):
    user_id = make_user(client, suffix='dvnf')
    make_account_and_deposit(client, user_id, amount=500)
    resp = client.get('/api/reports/daily-volumes')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1
    assert 'date' in data[0]
    assert 'count' in data[0]
    assert 'total' in data[0]


def test_daily_volumes_with_from(client):
    user_id = make_user(client, suffix='dvwf')
    make_account_and_deposit(client, user_id, amount=100)
    today = datetime.utcnow().strftime('%Y-%m-%d')
    resp = client.get(f'/api/reports/daily-volumes?from={today}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1


def test_daily_volumes_with_to(client):
    user_id = make_user(client, suffix='dvwt')
    make_account_and_deposit(client, user_id, amount=100)
    # Use tomorrow so the `<=` filter at midnight of to_date still includes today's transactions
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
    resp = client.get(f'/api/reports/daily-volumes?to={tomorrow}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1


def test_daily_volumes_with_both(client):
    user_id = make_user(client, suffix='dvwb')
    make_account_and_deposit(client, user_id, amount=100)
    today = datetime.utcnow().strftime('%Y-%m-%d')
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
    resp = client.get(f'/api/reports/daily-volumes?from={today}&to={tomorrow}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1


def test_daily_volumes_accumulation(client):
    """Two transactions on the same day → the 'day already in volumes' else branch is hit."""
    user_id = make_user(client, suffix='dvacc')
    acc_id = make_account_and_deposit(client, user_id, amount=500)
    # Second deposit on same day
    client.post(f'/api/accounts/{acc_id}/deposit', json={'amount': 200})
    resp = client.get('/api/reports/daily-volumes')
    assert resp.status_code == 200
    data = resp.get_json()
    # Both deposits land on today; count should be >= 2
    assert len(data) >= 1
    today_entry = data[0]
    assert today_entry['count'] >= 2
    assert today_entry['total'] >= 700.0
