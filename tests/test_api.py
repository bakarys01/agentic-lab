from fastapi.testclient import TestClient as BaseTestClient
from uuid import uuid4, UUID
import asyncio
import sqlite3
import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from backend.api import create_api_app
from backend.storage import Store


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'api.sqlite3'))


class TestClient(BaseTestClient):
    __test__ = False

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.headers['X-Requested-With'] = 'fetch'
        response = self.post('/api/auth/register', json={'email': f'{uuid4()}@example.com', 'password': 'test-password-123'})
        assert response.status_code == 201, response.text
        self.headers['X-CSRF-Token'] = response.json()['csrf_token']
        self.conversation_id = self.post('/api/conversations').json()['id']

    def post(self, url, **kwargs):
        if url == '/api/chat':
            kwargs['json'] = {'conversation_id': self.conversation_id, 'request_id': str(uuid4()), **kwargs.get('json', {})}
        return super().post(url, **kwargs)


class FakeConcierge:
    def answer_query_with_metadata(self, query: str, history=None):
        return {
            "answer": "This is a test answer.",
            "agents_used": ["research"],
            "request_id": "req-123",
            "latency_ms": 321,
        }

    def get_health(self):
        return {
            "concierge": {"status": "available"},
            "policy": {"status": "available"},
            "research": {"status": "available"},
        }


def test_conversation_rename_is_persistent_validated_and_owner_scoped():
    app = create_api_app(concierge=FakeConcierge())
    owner = TestClient(app)
    url = f'/api/conversations/{owner.conversation_id}'
    assert owner.patch(url, json={'title': '  My coverage  '}).json()['title'] == 'My coverage'
    assert owner.get('/api/conversations').json()['conversations'][0]['title'] == 'My coverage'
    assert owner.patch(url, json={'title': '   '}).status_code == 422
    assert owner.patch(url, json={'title': 'x' * 81}).status_code == 422
    assert owner.patch(url, json={'title': 'Valid'}, headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    other = TestClient(app)
    assert other.patch(url, json={'title': 'Stolen'}).status_code == 404
    assert owner.get('/api/conversations').json()['conversations'][0]['title'] == 'My coverage'


def test_manual_title_is_not_replaced_by_first_message():
    client = TestClient(create_api_app(concierge=FakeConcierge()))
    url = f'/api/conversations/{client.conversation_id}'
    assert client.patch(url, json={'title': 'New conversation'}).status_code == 200
    assert client.post('/api/chat', json={'message': 'First question'}).status_code == 200
    assert client.get('/api/conversations').json()['conversations'][0]['title'] == 'New conversation'


def test_existing_conversation_database_gains_custom_title_column(tmp_path):
    path = tmp_path / 'legacy.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE conversations (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, title TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL)')
    Store(path)
    with sqlite3.connect(path) as db:
        columns = {row[1] for row in db.execute('PRAGMA table_info(conversations)')}
    assert 'title_custom' in columns


def test_chat_endpoint_returns_metadata():
    app = create_api_app(concierge=FakeConcierge())
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "What is sleep apnea?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "This is a test answer."
    assert payload["agents_used"] == ["research"]
    assert UUID(payload["request_id"])
    assert payload["latency_ms"] == 321


def test_chat_endpoint_rejects_empty_message():
    app = create_api_app(concierge=FakeConcierge())
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "   "})

    assert response.status_code == 400
    assert "message" in response.json()["detail"]


def test_health_endpoint_returns_status():
    app = create_api_app(concierge=FakeConcierge())
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["services"]["concierge"]["status"] == "available"


def test_health_includes_new_specialists_in_legacy_payload():
    class ExpandedConcierge(FakeConcierge):
        def get_health(self):
            return {
                **super().get_health(),
                "healthcare_provider": {"status": "available"},
            }

    response = TestClient(create_api_app(concierge=ExpandedConcierge())).get(
        "/api/health"
    )

    assert response.json()["services"]["healthcare_provider"] == {
        "status": "available"
    }


def test_chat_can_call_async_specialist_from_sync_tool():
    class AsyncToolConcierge(FakeConcierge):
        def answer_query_with_metadata(self, query, history=None):
            async def specialist():
                return query
            return {"answer": asyncio.run(specialist()), "agents_used": ["policy"]}

    response = TestClient(create_api_app(AsyncToolConcierge())).post(
        "/api/chat", json={"message": " Coverage? "}
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Coverage?"


def test_default_factory_connects_real_concierge(monkeypatch):
    import backend.api as api
    monkeypatch.setattr(api, "build_concierge", FakeConcierge)
    response = TestClient(api.create_api_app()).post("/api/chat", json={"message": "Hello"})
    assert response.json()["answer"] == "This is a test answer."


def test_missing_concierge_returns_unavailable(monkeypatch):
    import backend.api as api

    def unavailable_concierge():
        raise RuntimeError("Concierge unavailable")

    monkeypatch.setattr(api, "build_concierge", unavailable_concierge)
    client = TestClient(api.create_api_app())
    assert client.get("/api/health").json()["status"] == "degraded"
    assert client.post("/api/chat", json={"message": "Hello"}).status_code == 503


@pytest.mark.parametrize("health", [None, {}, {"status": "ok", "services": {"policy": {"status": "unavailable"}}}])
def test_health_does_not_report_unavailable_services_as_ok(health):
    class UnhealthyConcierge(FakeConcierge):
        def get_health(self):
            return health
    response = TestClient(create_api_app(UnhealthyConcierge())).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


def test_chat_rejects_excessively_long_requests():
    response = TestClient(create_api_app(FakeConcierge())).post("/api/chat", json={"message": "a" * 8001})
    assert response.status_code == 422


@pytest.mark.parametrize("error, status", [(TimeoutError("private"), 504), (RuntimeError("private"), 502)])
def test_chat_errors_do_not_expose_internal_details(error, status):
    class FailingConcierge(FakeConcierge):
        def answer_query_with_metadata(self, query, history=None):
            raise error
    response = TestClient(create_api_app(FailingConcierge())).post("/api/chat", json={"message": "Hello"})
    assert response.status_code == status
    assert "private" not in response.text


@pytest.mark.parametrize("payload", [None, {}, {"answer": " "}, {"answer": 42},
    {"answer": "ok", "agents_used": "policy"}, {"answer": "ok", "latency_ms": "invalid"}])
def test_invalid_agent_payload_returns_sanitized_gateway_error(payload):
    class InvalidConcierge(FakeConcierge):
        def answer_query_with_metadata(self, query, history=None):
            return payload
    client = TestClient(create_api_app(InvalidConcierge()), raise_server_exceptions=False)
    response = client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code == 502
    assert response.json()["detail"] == "The healthcare concierge is currently unavailable."


def test_busy_concierge_rejects_queued_requests_and_recovers():
    started = Event()
    release = Event()

    class BlockingConcierge(FakeConcierge):
        def answer_query_with_metadata(self, query, history=None):
            started.set()
            assert release.wait(timeout=5)
            return super().answer_query_with_metadata(query)

    client = TestClient(create_api_app(BlockingConcierge()))
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(client.post, "/api/chat", json={"message": "First"})
        assert started.wait(timeout=5)
        try:
            second = executor.submit(client.post, "/api/chat", json={"message": "Second"})
            response = second.result(timeout=2)
            assert response.status_code == 503
            assert "busy" in response.json()["detail"]
        finally:
            release.set()
        assert first.result(timeout=5).status_code == 200
    assert client.post("/api/chat", json={"message": "After"}).status_code == 200


def test_agent_failure_releases_busy_lock():
    class RecoveringConcierge(FakeConcierge):
        def answer_query_with_metadata(self, query, history=None):
            if query == "Fail":
                raise RuntimeError("private")
            return super().answer_query_with_metadata(query)
    client = TestClient(create_api_app(RecoveringConcierge()))
    assert client.post("/api/chat", json={"message": "Fail"}).status_code == 502
    assert client.post("/api/chat", json={"message": "Recover"}).status_code == 200
