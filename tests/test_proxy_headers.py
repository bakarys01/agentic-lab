import asyncio

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def forwarded_scope(peer_ip):
    observed = {}

    async def app(scope, receive, send):
        observed.update(scope)

    middleware = ProxyHeadersMiddleware(
        app,
        trusted_hosts=["172.30.50.2"],
    )

    scope = {
        "type": "http",
        "scheme": "http",
        "client": (peer_ip, 12345),
        "headers": [
            (b"x-forwarded-for", b"203.0.113.10"),
            (b"x-forwarded-proto", b"https"),
        ],
    }

    asyncio.run(middleware(scope, None, None))
    return observed


def test_trusted_proxy_can_forward_client_and_scheme():
    scope = forwarded_scope("172.30.50.2")

    assert scope["scheme"] == "https"
    assert scope["client"][0] == "203.0.113.10"


def test_untrusted_client_cannot_spoof_headers():
    scope = forwarded_scope("172.30.50.130")

    assert scope["scheme"] == "http"
    assert scope["client"][0] == "172.30.50.130"