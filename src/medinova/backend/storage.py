"""Local, transactional storage. Each operation owns its SQLite connection."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
import uuid

from fastapi import HTTPException


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    csrf_token TEXT NOT NULL, expires_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
                    title_custom INTEGER NOT NULL DEFAULT 0,
                    title_generated INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    content TEXT NOT NULL, status TEXT NOT NULL, response TEXT);
                CREATE TABLE IF NOT EXISTS messages (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    request_id TEXT NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
                    role TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS conversations_owner ON conversations(user_id, updated_at);
                CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id, sequence);
            ''')
            if 'title_custom' not in {row['name'] for row in db.execute('PRAGMA table_info(conversations)')}:
                db.execute('ALTER TABLE conversations ADD COLUMN title_custom INTEGER NOT NULL DEFAULT 0')
            if 'title_generated' not in {row['name'] for row in db.execute('PRAGMA table_info(conversations)')}:
                db.execute('ALTER TABLE conversations ADD COLUMN title_generated INTEGER NOT NULL DEFAULT 0')
            # This application runs one worker. Interrupted turns remain retryable.
            db.execute("UPDATE requests SET status='failed' WHERE status='pending'")
            db.execute("UPDATE messages SET status='failed' WHERE status='pending'")
            db.execute('DELETE FROM sessions WHERE expires_at <= ?', (time.time(),))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def owned(db, user_id, conversation_id):
        row = db.execute('SELECT id,title,updated_at FROM conversations WHERE id=? AND user_id=?', (conversation_id, user_id)).fetchone()
        if row is None:
            raise HTTPException(404, 'Conversation not found.')
        return dict(row)

    def conversations(self, user_id):
        with self.connect() as db:
            rows = db.execute('SELECT id,title,updated_at,(title_custom OR title_generated) AS title_ready FROM conversations WHERE user_id=? ORDER BY updated_at DESC', (user_id,))
            return [{**dict(row), 'title_ready': bool(row['title_ready'])} for row in rows]

    def create_conversation(self, user_id):
        result = {'id': str(uuid.uuid4()), 'title': 'New conversation', 'updated_at': time.time()}
        with self.connect() as db:
            db.execute('INSERT INTO conversations(id,user_id,title,created_at,updated_at) VALUES (?,?,?,?,?)', (result['id'], user_id, result['title'], result['updated_at'], result['updated_at']))
        return result

    def rename_conversation(self, user_id, conversation_id, title):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.owned(db, user_id, conversation_id)
            updated_at = time.time()
            db.execute('UPDATE conversations SET title=?, title_custom=1, updated_at=? WHERE id=?', (title, updated_at, conversation_id))
        return {'id': conversation_id, 'title': title, 'updated_at': updated_at}

    def apply_generated_title(self, conversation_id, title):
        title = ' '.join(title.split())
        if not title or len(title) > 80:
            raise ValueError('Generated title must contain 1 to 80 characters.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            updated = db.execute(
                'UPDATE conversations SET title=?, title_generated=1, updated_at=? WHERE id=? AND title_custom=0 AND title_generated=0',
                (title, time.time(), conversation_id),
            )
            return updated.rowcount == 1

    def messages(self, user_id, conversation_id):
        with self.connect() as db:
            self.owned(db, user_id, conversation_id)
            return [dict(row) for row in db.execute('SELECT id,request_id,role,content,status,created_at FROM messages WHERE conversation_id=? ORDER BY sequence', (conversation_id,))]

    def delete_conversation(self, user_id, conversation_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.owned(db, user_id, conversation_id)
            if db.execute("SELECT 1 FROM requests WHERE conversation_id=? AND status='pending'", (conversation_id,)).fetchone():
                raise HTTPException(409, 'A response is in progress.')
            db.execute('DELETE FROM conversations WHERE id=?', (conversation_id,))

    def begin_turn(self, user_id, conversation_id, request_id, content):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.owned(db, user_id, conversation_id)
            row = db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
            if row:
                if row['conversation_id'] != conversation_id or row['content'] != content:
                    raise HTTPException(409, 'Request identifier already used.')
                if row['status'] == 'complete':
                    return json.loads(row['response'])
                if row['status'] == 'pending':
                    raise HTTPException(409, 'A response is in progress.')
                db.execute("UPDATE requests SET status='pending' WHERE id=?", (request_id,))
                # A failed older turn retried later becomes the latest turn.
                db.execute('DELETE FROM messages WHERE request_id=?', (request_id,))
                self._insert_message(db, conversation_id, request_id, 'user', content, 'pending')
            else:
                db.execute('INSERT INTO requests VALUES (?,?,?,?,NULL)', (request_id, conversation_id, content, 'pending'))
                self._insert_message(db, conversation_id, request_id, 'user', content, 'pending')
            db.execute("UPDATE conversations SET title=CASE WHEN title_custom=0 AND title_generated=0 AND title='New conversation' THEN ? ELSE title END, updated_at=? WHERE id=?", (content[:80], time.time(), conversation_id))
        return None

    @staticmethod
    def _insert_message(db, conversation_id, request_id, role, content, status):
        db.execute('INSERT INTO messages(id,conversation_id,request_id,role,content,status,created_at) VALUES (?,?,?,?,?,?,?)', (str(uuid.uuid4()), conversation_id, request_id, role, content, status, time.time()))

    def finish_turn(self, conversation_id, request_id, response):
        with self.connect() as db:
            db.execute("UPDATE requests SET status='complete', response=? WHERE id=?", (json.dumps(response), request_id))
            db.execute("UPDATE messages SET status='complete' WHERE request_id=?", (request_id,))
            self._insert_message(db, conversation_id, request_id, 'assistant', response['answer'], 'complete')
            db.execute('UPDATE conversations SET updated_at=? WHERE id=?', (time.time(), conversation_id))
            eligible = db.execute('SELECT title_custom,title_generated FROM conversations WHERE id=?', (conversation_id,)).fetchone()
            completed = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=? AND role='assistant' AND status='complete'", (conversation_id,)).fetchone()[0]
            return completed == 1 and eligible['title_custom'] == 0 and eligible['title_generated'] == 0

    def fail_turn(self, request_id):
        with self.connect() as db:
            db.execute("UPDATE requests SET status='failed' WHERE id=?", (request_id,))
            db.execute("UPDATE messages SET status='failed' WHERE request_id=?", (request_id,))

    def history(self, conversation_id):
        with self.connect() as db:
            rows = db.execute("SELECT r.content,r.response FROM requests r JOIN messages m ON m.request_id=r.id AND m.role='assistant' WHERE r.conversation_id=? AND r.status='complete' ORDER BY m.sequence DESC LIMIT 6", (conversation_id,)).fetchall()
        pairs = []
        size = 0
        for row in rows:
            answer = json.loads(row['response'])['answer']
            size += len(row['content']) + len(answer)
            if size > 16000:
                break
            pairs.append([{'role': 'user', 'content': row['content']}, {'role': 'assistant', 'content': answer}])
        return [message for pair in reversed(pairs) for message in pair]
