import uuid

from fastapi.testclient import TestClient

from medinova.backend.api import create_api_app
from test_auth import register


class RecordingAgent:
    def __init__(self):
        self.calls = []

    def answer_query_with_metadata(self, message, history=None):
        self.calls.append((message, history))
        if message == 'fail' and len(self.calls) == 1:
            raise RuntimeError('private error')
        return {'answer': f'Answer to {message}', 'agents_used': [], 'latency_ms': 0}


def setup(tmp_path):
    agent = RecordingAgent()
    client = TestClient(create_api_app(agent, db_path=tmp_path/'history.sqlite3'))
    register(client)
    return client, agent, client.post('/api/conversations').json()['id']


def send(client, conversation, message='hello', request_id=None):
    return client.post('/api/chat', json={'message': message, 'conversation_id': conversation, 'request_id': request_id or str(uuid.uuid4())})


def test_history_context_idempotency_and_deletion(tmp_path):
    client, agent, conversation = setup(tmp_path)
    key = str(uuid.uuid4())
    first = send(client, conversation, request_id=key)
    assert first.status_code == 200
    assert send(client, conversation, request_id=key).json() == first.json()
    assert len(agent.calls) == 1
    assert send(client, conversation, 'follow-up').status_code == 200
    assert agent.calls[-1][1] == [{'role':'user','content':'hello'}, {'role':'assistant','content':'Answer to hello'}]
    other = client.post('/api/conversations').json()['id']
    send(client, other, 'fresh')
    assert agent.calls[-1][1] == []
    messages = client.get(f'/api/conversations/{conversation}/messages').json()['messages']
    assert len(messages) == 4
    assert all(m['status'] == 'complete' for m in messages)
    assert client.delete(f'/api/conversations/{conversation}').status_code == 204
    assert client.get(f'/api/conversations/{conversation}/messages').status_code == 404
    assert len(client.get('/api/conversations').json()['conversations']) == 1


def test_failed_retry_uses_same_turn_and_old_failures_excluded(tmp_path):
    client, agent, conversation = setup(tmp_path)
    key = str(uuid.uuid4())
    assert send(client, conversation, 'fail', key).status_code == 502
    messages = client.get(f'/api/conversations/{conversation}/messages').json()['messages']
    assert len(messages) == 1 and messages[0]['status'] == 'failed'
    assert send(client, conversation, 'fail', key).status_code == 200
    assert agent.calls[-1][1] == []
    assert len(client.get(f'/api/conversations/{conversation}/messages').json()['messages']) == 2
    assert send(client, conversation, 'different', key).status_code == 409


def test_persistence_across_app_restart_and_session_revocation(tmp_path):
    client, agent, conversation = setup(tmp_path)
    send(client, conversation, 'remember me')
    restarted = TestClient(create_api_app(RecordingAgent(), db_path=tmp_path/'history.sqlite3'))
    restarted.cookies.update(client.cookies)
    assert restarted.get('/api/auth/me').status_code == 200
    assert len(restarted.get(f'/api/conversations/{conversation}/messages').json()['messages']) == 2
    old_cookie = dict(client.cookies)
    assert client.post('/api/auth/logout').status_code == 204
    restarted.cookies.update(old_cookie)
    assert restarted.get('/api/auth/me').status_code == 401


def test_pending_turn_blocks_deletion_and_interrupted_request_is_retryable(tmp_path):
    from medinova.backend.storage import Store
    client, agent, conversation = setup(tmp_path)
    user_id = client.get('/api/auth/me').json()['user']['id']
    store = Store(tmp_path/'history.sqlite3')
    key = str(uuid.uuid4())
    store.begin_turn(user_id, conversation, key, 'pending')
    assert client.delete(f'/api/conversations/{conversation}').status_code == 409
    assert send(client, conversation, 'pending', key).status_code == 409
    Store(tmp_path/'history.sqlite3')
    assert send(client, conversation, 'pending', key).status_code == 200


def test_retry_old_failure_keeps_messages_in_completed_turn_order(tmp_path):
    client, agent, conversation = setup(tmp_path)
    key = str(uuid.uuid4())
    send(client, conversation, 'fail', key)
    send(client, conversation, 'next')
    send(client, conversation, 'fail', key)
    messages = client.get(f'/api/conversations/{conversation}/messages').json()['messages']
    assert [m['content'] for m in messages] == ['next','Answer to next','fail','Answer to fail']
