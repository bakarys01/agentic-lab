import uuid

import pytest
from fastapi.testclient import TestClient

from medinova.backend.api import create_api_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_api_app(object(), db_path=tmp_path / 'test.sqlite3'))


def register(client, email='person@example.com'):
    client.headers['X-Requested-With'] = 'fetch'
    response = client.post('/api/auth/register', json={'email': email, 'password': 'secure-passphrase-123'})
    assert response.status_code == 201, response.text
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    return response


def test_registration_login_logout(client):
    response = register(client)
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert client.get('/api/auth/me').json()['user']['email'] == 'person@example.com'
    assert client.post('/api/auth/logout').status_code == 204
    assert client.get('/api/auth/me').status_code == 401
    response = client.post('/api/auth/login', json={'email': 'PERSON@example.com', 'password': 'secure-passphrase-123'})
    assert response.status_code == 200
    assert 'password' not in response.text


def test_csrf_and_origin_required(client):
    assert client.post('/api/auth/register', json={'email': 'x@y.com', 'password': '123456789012'}).status_code == 403
    register(client)
    assert client.post('/api/conversations').status_code == 201
    assert client.post('/api/conversations', headers={'X-CSRF-Token': 'bad'}).status_code == 403
    assert client.post('/api/conversations', headers={'Origin': 'https://evil.example'}).status_code == 403


def test_no_private_access_anonymous(client):
    assert client.get('/api/conversations').status_code == 401
    assert client.get('/api/conversations').headers['cache-control'] == 'no-store'


def test_invalid_and_duplicate_accounts(client):
    register(client)
    assert client.post('/api/auth/register', json={'email': 'person@example.com', 'password': 'secure-passphrase-123'}).status_code == 409
    assert client.post('/api/auth/login', json={'email': 'person@example.com', 'password': 'wrong-password'}).status_code == 401
    assert client.post('/api/auth/register', json={'email': 'bad', 'password': 'short'}).status_code == 422


def test_user_isolation(client):
    register(client)
    conversation = client.post('/api/conversations').json()['id']
    other = TestClient(client.app)
    register(other, 'other@example.com')
    assert other.get('/api/conversations').json()['conversations'] == []
    assert other.get(f'/api/conversations/{conversation}/messages').status_code == 404
    assert other.delete(f'/api/conversations/{conversation}').status_code == 404
    assert other.post('/api/chat', json={'message': 'hello', 'conversation_id': conversation, 'request_id': str(uuid.uuid4())}).status_code == 404

def test_password_and_session_tokens_are_not_stored_plaintext(client, tmp_path):
    import sqlite3
    from contextlib import closing
    register(client)
    with closing(sqlite3.connect(tmp_path/'test.sqlite3')) as db:
        hashed = db.execute('SELECT password_hash FROM users').fetchone()[0]
        token = db.execute('SELECT token_hash FROM sessions').fetchone()[0]
    assert 'secure-passphrase-123' not in hashed
    assert token != client.cookies.get('medinova_session')
    assert len(token) == 64


def test_expired_and_tampered_sessions_are_rejected(client, tmp_path):
    import sqlite3
    from contextlib import closing
    register(client)
    with closing(sqlite3.connect(tmp_path/'test.sqlite3')) as db:
        db.execute('UPDATE sessions SET expires_at=0')
        db.commit()
    assert client.get('/api/auth/me').status_code == 401
    client.cookies.clear()
    client.cookies.set('medinova_session', 'invalid')
    assert client.get('/api/conversations').status_code == 401


def test_auth_rate_limit_and_password_validation_do_not_echo_secrets(client):
    client.headers['X-Requested-With'] = 'fetch'
    invalid = client.post('/api/auth/register', json={'email':'x@y.com','password':'p@ss'})
    assert invalid.status_code == 422
    assert 'p@ss' not in invalid.text
    assert all('input' not in error for error in invalid.json()['detail'])
    for _ in range(10):
        assert client.post('/api/auth/login', json={'email':'nobody@example.com','password':'bad-password-123'}).status_code == 401
    assert client.post('/api/auth/login', json={'email':'nobody@example.com','password':'bad-password-123'}).status_code == 429


def test_secure_cookie_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv('SESSION_COOKIE_SECURE', 'true')
    secure = TestClient(create_api_app(object(), db_path=tmp_path/'secure.sqlite3'), base_url='https://testserver')
    response = register(secure)
    assert '; Secure' in response.headers['set-cookie']
    assert 'SameSite=strict' in response.headers['set-cookie']
