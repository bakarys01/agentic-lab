"""Local account authentication and revocable server-side sessions."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from threading import Lock
from uuid import uuid4

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from starlette.responses import JSONResponse

COOKIE = 'medinova_session'
SESSION_SECONDS = 7 * 24 * 3600
ITERATIONS = 600_000


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f'{salt}${digest}'


def verify_password(password, stored):
    salt = stored.split('$', 1)[0]
    return hmac.compare_digest(password_hash(password, salt), stored)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def validate_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value


class Limiter:
    def __init__(self):
        self.entries = {}
        self.lock = Lock()

    def check(self, key, maximum):
        now = time.monotonic()
        with self.lock:
            self.entries = {k: tuple(t for t in v if t > now - 60) for k, v in self.entries.items() if v and v[-1] > now - 60}
            entries = self.entries.get(key, ())
            if len(entries) >= maximum:
                raise HTTPException(429, 'Too many requests. Please wait a minute.', headers={'Retry-After': '60'})
            self.entries[key] = (*entries, now)


def install_auth(app, get_store):
    limiter = Limiter()
    dummy_hash = password_hash('dummy-password-for-timing')
    secure_cookie = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

    @app.middleware('http')
    async def api_security(request, call_next):
        if request.url.path.startswith('/api/'):
            if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
                origin = request.headers.get('origin')
                expected = str(request.base_url).rstrip('/')
                if request.headers.get('x-requested-with') != 'fetch' or (origin is not None and origin != expected):
                    return JSONResponse({'detail': 'Request origin could not be verified.'}, status_code=403, headers={'Cache-Control': 'no-store'})
            response = await call_next(request)
            response.headers['Cache-Control'] = 'no-store'
            return response
        return await call_next(request)

    def identity(request: Request):
        token = request.cookies.get(COOKIE, '')
        if not token or len(token) > 256:
            raise HTTPException(401, 'Please sign in.')
        with get_store().connect() as db:
            row = db.execute('SELECT u.id,u.email,s.csrf_token FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?', (token_hash(token), time.time())).fetchone()
        if row is None:
            raise HTTPException(401, 'Please sign in.')
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            supplied = request.headers.get('x-csrf-token', '')
            if not hmac.compare_digest(supplied, row['csrf_token']):
                raise HTTPException(403, 'Session verification failed. Reload and try again.')
        limiter.check(('user', row['id']), 120)
        return {'user': {'id': row['id'], 'email': row['email']}, 'csrf_token': row['csrf_token']}

    def issue_session(user, request, response):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with get_store().connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=? OR expires_at<=?', (token_hash(request.cookies.get(COOKIE, '')), time.time()))
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (token_hash(token), user['id'], csrf, time.time() + SESSION_SECONDS))
        response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, secure=secure_cookie, samesite='strict', path='/')
        return {'user': user, 'csrf_token': csrf}

    def auth_limit(request):
        limiter.check(('auth', request.client.host if request.client else 'local'), 10)

    @app.post('/api/auth/register', status_code=201)
    def register(credentials: Credentials, request: Request, response: Response):
        auth_limit(request)
        user = {'id': str(uuid4()), 'email': credentials.email}
        hashed = password_hash(credentials.password)
        try:
            with get_store().connect() as db:
                db.execute('INSERT INTO users VALUES (?,?,?,?)', (user['id'], user['email'], hashed, time.time()))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, 'Unable to create this account. Try signing in.') from exc
        return issue_session(user, request, response)

    @app.post('/api/auth/login')
    def login(credentials: Credentials, request: Request, response: Response):
        auth_limit(request)
        with get_store().connect() as db:
            row = db.execute('SELECT id,email,password_hash FROM users WHERE email=?', (credentials.email,)).fetchone()
        valid = verify_password(credentials.password, row['password_hash'] if row else dummy_hash)
        if row is None or not valid:
            raise HTTPException(401, 'Email or password is incorrect.')
        return issue_session({'id': row['id'], 'email': row['email']}, request, response)

    @app.get('/api/auth/me')
    def me(request: Request):
        return identity(request)

    @app.post('/api/auth/logout', status_code=204)
    def logout(request: Request):
        identity(request)
        with get_store().connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(request.cookies.get(COOKIE, '')),))
        response = Response(status_code=204)
        response.delete_cookie(COOKIE, path='/', httponly=True, secure=secure_cookie, samesite='strict')
        return response

    return identity
