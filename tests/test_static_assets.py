"""Frontend updates must not leave browsers running an older chat client."""

import pytest
from fastapi.testclient import TestClient

from backend.api import create_api_app


@pytest.fixture
def client():
    with TestClient(create_api_app(concierge=object())) as test_client:
        yield test_client


@pytest.mark.parametrize("path", ["/", "/index.html", "/styles.css", "/app.js"])
def test_frontend_assets_are_not_cached(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.content
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/", "/styles.css", "/app.js"])
@pytest.mark.parametrize("validator", ["etag", "last-modified"])
def test_old_browser_validators_still_receive_current_assets(client, path, validator):
    original = client.get(path)
    request_header = "if-none-match" if validator == "etag" else "if-modified-since"

    response = client.get(path, headers={request_header: original.headers[validator]})

    # A browser may retain assets cached before no-store was introduced.
    assert response.status_code == 200
    assert response.content == original.content
    assert response.headers["cache-control"] == "no-store"


def test_frontend_head_preserves_no_store(client):
    response = client.head("/app.js")

    assert response.status_code == 200
    assert not response.content
    assert response.headers["cache-control"] == "no-store"
