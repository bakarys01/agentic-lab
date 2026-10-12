"""Contract checks for medication lookups exposed through MCP."""

import json

import pytest

from medinova.mcp_servers.medication import get_medication


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.rows = [
            [{"cis": "60043077", "name": "OXCARBAZEPINE VIATRIS 300 mg"}],
            [{"cip7": "3798286", "cip13": "3400937982863", "label": "50 comprimé(s)"}],
            [{"substance_name": "OXCARBAZÉPINE", "substance_dosage": "300 mg"}],
        ]

    def execute(self, sql, params):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows.pop(0)


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_value = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def cursor(self, **_):
        return FakeConnection(self.cursor_value)

    def execute(self, sql, params):
        self.cursor_value.execute(sql, params)

    def fetchall(self):
        return self.cursor_value.fetchall()


def test_get_medication_returns_structured_matches(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr("psycopg.connect", lambda: FakeConnection(cursor))

    result = json.loads(get_medication("  oxcarbazepine  "))

    assert result["medications"][0]["cis"] == "60043077"
    assert result["medications"][0]["presentations"][0]["cip13"] == "3400937982863"
    assert result["medications"][0]["compositions"][0]["substance_dosage"] == "300 mg"
    assert cursor.calls[0][1][0] == "oxcarbazepine"
    assert all("%s" in sql for sql, _ in cursor.calls)


def test_get_medication_returns_empty_list_for_unknown_name(monkeypatch):
    cursor = FakeCursor()
    cursor.rows = [[]]
    monkeypatch.setattr("psycopg.connect", lambda: FakeConnection(cursor))

    assert json.loads(get_medication("not-in-sample")) == {"medications": []}
    assert len(cursor.calls) == 1


def test_get_medication_escapes_sql_like_wildcards(monkeypatch):
    cursor = FakeCursor()
    cursor.rows = [[]]
    monkeypatch.setattr("psycopg.connect", lambda: FakeConnection(cursor))

    get_medication("10%_\\")

    assert cursor.calls[0][1][1] == r"%10\%\_\\%"


def test_get_medication_extracts_explicit_cis_from_question(monkeypatch):
    cursor = FakeCursor()
    cursor.rows = [[]]
    monkeypatch.setattr("psycopg.connect", lambda: FakeConnection(cursor))

    get_medication("What is the substance for CIS 60043077?")

    assert cursor.calls[0][1][0] == "60043077"


@pytest.mark.parametrize("query", ["", "   ", "x" * 101])
def test_get_medication_rejects_invalid_query(query):
    with pytest.raises(ValueError, match="1 to 100"):
        get_medication(query)
