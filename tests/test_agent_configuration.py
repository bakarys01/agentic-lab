import pytest

from a2a_clients import client_utils


@pytest.mark.parametrize('name,port', [('policy', '9999'), ('research', '9998')])
def test_specialist_url_respects_port_and_public_url(monkeypatch, name, port):
    prefix = name.upper()
    monkeypatch.delenv(f'{prefix}_AGENT_PUBLIC_URL', raising=False)
    monkeypatch.delenv(f'{prefix}_AGENT_PORT', raising=False)
    assert client_utils.get_agent_url(name) == f'http://127.0.0.1:{port}'
    monkeypatch.setenv(f'{prefix}_AGENT_PORT', '12345')
    assert client_utils.get_agent_url(name) == 'http://127.0.0.1:12345'
    monkeypatch.setenv(f'{prefix}_AGENT_PUBLIC_URL', 'http://localhost:23456/')
    assert client_utils.get_agent_url(name) == 'http://localhost:23456'


@pytest.mark.parametrize('name', ['policy', 'research'])
def test_tools_use_configured_specialist_url(monkeypatch, name):
    import asyncio

    monkeypatch.setenv(f'{name.upper()}_AGENT_PUBLIC_URL', 'http://localhost:23456')

    async def fake_ask(agent_url, question, timeout):
        assert agent_url == 'http://localhost:23456'
        assert question == 'Question'
        return 'Answer'

    monkeypatch.setattr(client_utils, 'ask_a2a_agent', fake_ask)
    assert asyncio.run(getattr(client_utils, f'ask_{name}_agent')('Question')) == 'Answer'
