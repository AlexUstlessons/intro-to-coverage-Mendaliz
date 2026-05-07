import pytest
from app.models import Account


# ---------------------------------------------------------------------------
# POST /api/users
# ---------------------------------------------------------------------------

def test_create_user_success(client):
    resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Alice'
    assert data['email'] == 'alice@example.com'
    assert data['is_email_verified'] is False


def test_create_user_invalid_email(client):
    resp = client.post('/api/users/', json={'name': 'Bob', 'email': 'not-an-email'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_create_user_duplicate_email(client):
    client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    resp = client.post('/api/users/', json={'name': 'Alice2', 'email': 'alice@example.com'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/users
# ---------------------------------------------------------------------------

def test_list_users_empty(client):
    resp = client.get('/api/users/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['items'] == []
    assert data['total'] == 0
    assert data['page'] == 1
    assert data['pages'] == 1


def test_list_users_with_data(client):
    client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    client.post('/api/users/', json={'name': 'Bob', 'email': 'bob@example.com'})
    resp = client.get('/api/users/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 2
    assert len(data['items']) == 2


def test_list_users_pagination(client):
    client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    client.post('/api/users/', json={'name': 'Bob', 'email': 'bob@example.com'})
    resp = client.get('/api/users/?per_page=1&page=2')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 2
    assert data['pages'] == 2
    assert data['page'] == 2
    assert len(data['items']) == 1


# ---------------------------------------------------------------------------
# GET /api/users/<id>
# ---------------------------------------------------------------------------

def test_get_user_success(client):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    resp = client.get(f'/api/users/{user_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == user_id
    assert data['name'] == 'Alice'


def test_get_user_not_found(client):
    resp = client.get('/api/users/99999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# PUT /api/users/<id>
# ---------------------------------------------------------------------------

def test_update_user_name_only(client):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    resp = client.put(f'/api/users/{user_id}', json={'name': 'Alicia'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Alicia'
    assert data['email'] == 'alice@example.com'


def test_update_user_email_only(client):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    resp = client.put(f'/api/users/{user_id}', json={'email': 'newalice@example.com'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['email'] == 'newalice@example.com'


def test_update_user_invalid_email(client):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    resp = client.put(f'/api/users/{user_id}', json={'email': 'bad-email'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_update_user_duplicate_email(client):
    client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    bob_resp = client.post('/api/users/', json={'name': 'Bob', 'email': 'bob@example.com'})
    bob_id = bob_resp.get_json()['id']
    resp = client.put(f'/api/users/{bob_id}', json={'email': 'alice@example.com'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_update_user_same_email(client):
    """Updating email to the same value should NOT raise duplicate error."""
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    resp = client.put(f'/api/users/{user_id}', json={'email': 'alice@example.com'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['email'] == 'alice@example.com'


def test_update_user_not_found(client):
    resp = client.put('/api/users/99999', json={'name': 'Ghost'})
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# DELETE /api/users/<id>
# ---------------------------------------------------------------------------

def test_delete_user_success(client):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    resp = client.delete(f'/api/users/{user_id}')
    assert resp.status_code == 200
    assert resp.get_json()['message'] == 'User deleted'
    # confirm it's gone
    get_resp = client.get(f'/api/users/{user_id}')
    assert get_resp.status_code == 404


def test_delete_user_has_accounts(client, db):
    create_resp = client.post('/api/users/', json={'name': 'C', 'email': 'c@example.com'})
    user_id = create_resp.get_json()['id']
    acct = Account(user_id=user_id, type='checking', balance=0)
    db.session.add(acct)
    db.session.commit()
    resp = client.delete(f'/api/users/{user_id}')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_delete_user_not_found(client):
    resp = client.delete('/api/users/99999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# POST /api/users/<id>/verify-email
# ---------------------------------------------------------------------------

def test_verify_email_success(client):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    resp = client.post(f'/api/users/{user_id}/verify-email')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['is_email_verified'] is True


def test_verify_email_already_verified(client):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    client.post(f'/api/users/{user_id}/verify-email')
    resp = client.post(f'/api/users/{user_id}/verify-email')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_verify_email_not_found(client):
    resp = client.post('/api/users/99999/verify-email')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


# ---------------------------------------------------------------------------
# GET /api/users/search
# ---------------------------------------------------------------------------

def test_search_users_by_name(client):
    client.post('/api/users/', json={'name': 'Alice Smith', 'email': 'alice@example.com'})
    client.post('/api/users/', json={'name': 'Bob Jones', 'email': 'bob@example.com'})
    resp = client.get('/api/users/search?q=Alice')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['name'] == 'Alice Smith'


def test_search_users_by_email(client):
    client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    client.post('/api/users/', json={'name': 'Bob', 'email': 'bob@example.com'})
    resp = client.get('/api/users/search?q=bob@')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['email'] == 'bob@example.com'


def test_search_users_empty_query(client):
    client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    resp = client.get('/api/users/search?q=')
    assert resp.status_code == 200
    data = resp.get_json()
    # empty query matches everyone via %%
    assert len(data) >= 1


# ---------------------------------------------------------------------------
# GET /api/users/<id>/summary
# ---------------------------------------------------------------------------

def test_get_user_summary_no_accounts(client):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    resp = client.get(f'/api/users/{user_id}/summary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['account_count'] == 0
    assert data['total_balance'] == 0.0
    assert data['accounts'] == []
    assert data['user']['id'] == user_id


def test_get_user_summary_with_accounts(client, db):
    create_resp = client.post('/api/users/', json={'name': 'Alice', 'email': 'alice@example.com'})
    user_id = create_resp.get_json()['id']
    acct1 = Account(user_id=user_id, type='checking', balance=100)
    acct2 = Account(user_id=user_id, type='savings', balance=200)
    db.session.add_all([acct1, acct2])
    db.session.commit()
    resp = client.get(f'/api/users/{user_id}/summary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['account_count'] == 2
    assert data['total_balance'] == pytest.approx(300.0)
    assert len(data['accounts']) == 2


def test_get_user_summary_not_found(client):
    resp = client.get('/api/users/99999/summary')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()
