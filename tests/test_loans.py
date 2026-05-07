from datetime import datetime, timedelta
from app.models import Loan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user_and_account(client, suffix='1', fund=10000):
    u = client.post('/api/users/', json={'name': f'U{suffix}', 'email': f'u{suffix}@t.com'})
    user_id = u.get_json()['id']
    a = client.post('/api/accounts/', json={'user_id': user_id, 'type': 'checking'})
    account_id = a.get_json()['id']
    if fund:
        client.post(f'/api/accounts/{account_id}/deposit', json={'amount': fund})
    return user_id, account_id


def apply_and_approve_loan(client, user_id, amount=1000, rate=0.12, term=12):
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': amount,
        'interest_rate': rate, 'term_months': term
    })
    loan_id = r.get_json()['id']
    client.post(f'/api/loans/{loan_id}/approve')
    return loan_id


# ---------------------------------------------------------------------------
# POST /api/loans/
# ---------------------------------------------------------------------------

def test_apply_for_loan_success(client):
    user_id, _ = make_user_and_account(client, suffix='s1')
    resp = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['status'] == 'pending'
    assert data['amount'] == 1000.0
    assert data['amount_paid'] == 0.0


def test_apply_for_loan_user_not_found(client):
    resp = client.post('/api/loans/', json={
        'user_id': 9999, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12
    })
    assert resp.status_code == 404


def test_apply_for_loan_zero_amount(client):
    user_id, _ = make_user_and_account(client, suffix='za')
    resp = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 0,
        'interest_rate': 0.12, 'term_months': 12
    })
    assert resp.status_code == 400


def test_apply_for_loan_negative_amount(client):
    user_id, _ = make_user_and_account(client, suffix='na')
    resp = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': -100,
        'interest_rate': 0.12, 'term_months': 12
    })
    assert resp.status_code == 400


def test_apply_for_loan_zero_rate(client):
    """rate=0 exercises the rate==0 branch in calculate_monthly_payment."""
    user_id, _ = make_user_and_account(client, suffix='zr')
    resp = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1200,
        'interest_rate': 0, 'term_months': 12
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['monthly_payment'] == 100.0  # 1200 / 12


def test_apply_for_loan_negative_rate(client):
    user_id, _ = make_user_and_account(client, suffix='nr')
    resp = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': -0.01, 'term_months': 12
    })
    assert resp.status_code == 400


def test_apply_for_loan_zero_term(client):
    user_id, _ = make_user_and_account(client, suffix='zt')
    resp = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 0
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/loans/<id>
# ---------------------------------------------------------------------------

def test_get_loan_success(client):
    user_id, _ = make_user_and_account(client, suffix='gl1')
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 500,
        'interest_rate': 0.1, 'term_months': 6
    })
    loan_id = r.get_json()['id']
    resp = client.get(f'/api/loans/{loan_id}')
    assert resp.status_code == 200
    assert resp.get_json()['id'] == loan_id


def test_get_loan_not_found(client):
    resp = client.get('/api/loans/9999')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/loans/user/<id>
# ---------------------------------------------------------------------------

def test_get_user_loans_empty(client):
    user_id, _ = make_user_and_account(client, suffix='ule')
    resp = client.get(f'/api/loans/user/{user_id}')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_user_loans_with_data(client):
    user_id, _ = make_user_and_account(client, suffix='uld')
    client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 800,
        'interest_rate': 0.08, 'term_months': 8
    })
    resp = client.get(f'/api/loans/user/{user_id}')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_get_user_loans_user_not_found(client):
    resp = client.get('/api/loans/user/9999')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/loans/<id>/approve
# ---------------------------------------------------------------------------

def test_approve_loan_success(client):
    user_id, _ = make_user_and_account(client, suffix='als')
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12
    })
    loan_id = r.get_json()['id']
    resp = client.post(f'/api/loans/{loan_id}/approve')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'approved'


def test_approve_loan_not_pending(client):
    """Approving an already-approved loan raises LoanNotPendingError."""
    user_id, _ = make_user_and_account(client, suffix='alnp')
    loan_id = apply_and_approve_loan(client, user_id)
    resp = client.post(f'/api/loans/{loan_id}/approve')
    assert resp.status_code == 400


def test_approve_loan_not_found(client):
    resp = client.post('/api/loans/9999/approve')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/loans/<id>/reject
# ---------------------------------------------------------------------------

def test_reject_loan_success(client):
    user_id, _ = make_user_and_account(client, suffix='rls')
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12
    })
    loan_id = r.get_json()['id']
    resp = client.post(f'/api/loans/{loan_id}/reject')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'rejected'


def test_reject_loan_not_pending(client):
    """Rejecting an already-rejected loan raises LoanNotPendingError."""
    user_id, _ = make_user_and_account(client, suffix='rlnp')
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12
    })
    loan_id = r.get_json()['id']
    client.post(f'/api/loans/{loan_id}/reject')
    resp = client.post(f'/api/loans/{loan_id}/reject')
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/loans/<id>/payment
# ---------------------------------------------------------------------------

def test_make_payment_success(client):
    user_id, account_id = make_user_and_account(client, suffix='mps')
    loan_id = apply_and_approve_loan(client, user_id, amount=1000, rate=0.12, term=12)
    resp = client.post(f'/api/loans/{loan_id}/payment', json={'account_id': account_id})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['amount_paid'] > 0


def test_make_payment_completes_loan(client):
    """Payment that brings amount_paid >= amount sets status to 'paid'."""
    user_id, account_id = make_user_and_account(client, suffix='mpcl', fund=10000)
    # Use a small amount and term=1 so monthly_payment >= loan.amount
    loan_id = apply_and_approve_loan(client, user_id, amount=100, rate=0.0, term=1)
    resp = client.post(f'/api/loans/{loan_id}/payment', json={'account_id': account_id})
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'paid'


def test_make_payment_already_paid(client):
    user_id, account_id = make_user_and_account(client, suffix='mpap', fund=10000)
    loan_id = apply_and_approve_loan(client, user_id, amount=100, rate=0.0, term=1)
    # First payment pays it off
    client.post(f'/api/loans/{loan_id}/payment', json={'account_id': account_id})
    # Second payment should fail with LoanAlreadyPaidError
    resp = client.post(f'/api/loans/{loan_id}/payment', json={'account_id': account_id})
    assert resp.status_code == 400


def test_make_payment_not_approved(client):
    """Pending loan raises LoanNotApprovedError."""
    user_id, account_id = make_user_and_account(client, suffix='mpna')
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12
    })
    loan_id = r.get_json()['id']
    resp = client.post(f'/api/loans/{loan_id}/payment', json={'account_id': account_id})
    assert resp.status_code == 400


def test_make_payment_insufficient_funds(client):
    user_id, account_id = make_user_and_account(client, suffix='mpif', fund=0)
    loan_id = apply_and_approve_loan(client, user_id, amount=1000, rate=0.12, term=12)
    resp = client.post(f'/api/loans/{loan_id}/payment', json={'account_id': account_id})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/loans/<id>/schedule
# ---------------------------------------------------------------------------

def test_get_payment_schedule(client):
    user_id, _ = make_user_and_account(client, suffix='gps')
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1200,
        'interest_rate': 0.12, 'term_months': 12
    })
    loan_id = r.get_json()['id']
    resp = client.get(f'/api/loans/{loan_id}/schedule')
    assert resp.status_code == 200
    schedule = resp.get_json()
    assert len(schedule) == 12
    assert 'month' in schedule[0]
    assert 'payment' in schedule[0]


# ---------------------------------------------------------------------------
# POST /api/loans/<id>/early-repayment
# ---------------------------------------------------------------------------

def test_early_repayment_success(client):
    user_id, account_id = make_user_and_account(client, suffix='ers', fund=10000)
    loan_id = apply_and_approve_loan(client, user_id, amount=1000, rate=0.12, term=12)
    resp = client.post(f'/api/loans/{loan_id}/early-repayment', json={'account_id': account_id})
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'paid'


def test_early_repayment_already_paid(client):
    user_id, account_id = make_user_and_account(client, suffix='erap', fund=10000)
    loan_id = apply_and_approve_loan(client, user_id, amount=100, rate=0.0, term=1)
    # Pay it off first
    client.post(f'/api/loans/{loan_id}/payment', json={'account_id': account_id})
    resp = client.post(f'/api/loans/{loan_id}/early-repayment', json={'account_id': account_id})
    assert resp.status_code == 400


def test_early_repayment_not_approved(client):
    """Pending loan raises LoanNotApprovedError."""
    user_id, account_id = make_user_and_account(client, suffix='erna')
    r = client.post('/api/loans/', json={
        'user_id': user_id, 'amount': 1000,
        'interest_rate': 0.12, 'term_months': 12
    })
    loan_id = r.get_json()['id']
    resp = client.post(f'/api/loans/{loan_id}/early-repayment', json={'account_id': account_id})
    assert resp.status_code == 400


def test_early_repayment_insufficient(client):
    user_id, account_id = make_user_and_account(client, suffix='eri', fund=0)
    loan_id = apply_and_approve_loan(client, user_id, amount=1000, rate=0.12, term=12)
    resp = client.post(f'/api/loans/{loan_id}/early-repayment', json={'account_id': account_id})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/loans/overdue
# ---------------------------------------------------------------------------

def test_get_overdue_loans_none(client):
    """Approved loan with recent created_at should NOT be overdue."""
    user_id, _ = make_user_and_account(client, suffix='goln')
    apply_and_approve_loan(client, user_id, amount=1000, rate=0.12, term=12)
    resp = client.get('/api/loans/overdue')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_overdue_loans_with_overdue(client, db):
    """Inject an old created_at to force the loan into overdue state."""
    user_id, _ = make_user_and_account(client, suffix='golwo')
    loan_id = apply_and_approve_loan(client, user_id, amount=1000, rate=0.12, term=12)
    # Backdate the loan's created_at so it is well past due
    loan_obj = Loan.query.get(loan_id)
    loan_obj.created_at = datetime.utcnow() - timedelta(days=400)
    db.session.commit()
    resp = client.get('/api/loans/overdue')
    assert resp.status_code == 200
    overdue = resp.get_json()
    assert len(overdue) == 1
    assert overdue[0]['id'] == loan_id
