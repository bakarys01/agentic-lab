# Accounts, history and concierge memory

## First use

Start the three services as described in the README, then open `http://127.0.0.1:8000`. Choose **Create an account**, enter an email address and a password of 12–128 characters, and submit. Registration signs you in automatically. Email addresses are normalized to lowercase; email ownership is not verified in this local version.

Use **New conversation** to start a separate thread. The first persisted question sets its title, even if agent execution subsequently fails. Select a thread in the history list to reload it. Refreshing the page restores the signed-in session and the last selected conversation (or the most recent conversation when no selection is saved).

Use **Delete conversation** and confirm to remove its messages and request records. Deletion is rejected while that conversation has a request running. **Sign out** revokes the current session and clears messages from the page.

## Storage and configuration

`DATABASE_PATH` defaults to `data/concierge.sqlite3`, relative to the project root. SQLite creates the initial tables automatically on first account/history access. No database server is required. SQLite files and their journal files are excluded from Git. Changing the path selects a different database; it does not migrate existing data.

| Table | Contents |
| --- | --- |
| `users` | User ID, unique normalized email, salted password hash and creation time |
| `sessions` | Hash of an opaque session token, owner, CSRF token and expiry |
| `conversations` | Owner, title and creation/update times |
| `requests` | Idempotency ID, conversation, input, pending/failed/complete state and saved response |
| `messages` | Ordered user/assistant content, request linkage and state |

Messages are stored as plain text in the local database; encryption at rest is not provided. Protect the database and backups as private information. Stop the backend before copying the database for a consistent offline backup, and restore it while the backend is stopped. Deleting a conversation does not erase copies already present in backups or retained by external model services.

## Authentication and authorization

Passwords use PBKDF2-HMAC-SHA256 with 600,000 iterations and a random salt. Passwords and raw session tokens are not stored in the database. The session cookie is HttpOnly, SameSite=Strict, scoped to `/`, and expires after seven days. Sessions remain valid across server restarts until expiry or explicit sign-out.

Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS. Its default is false for local HTTP development. Keep `BACKEND_HOST=127.0.0.1`; this release is not a public deployment configuration.

Every private route resolves the user from the session cookie. Supplied conversation IDs are checked against that user; another user's conversation returns 404. Clients never choose a `user_id` for access.

All mutation requests require `X-Requested-With: fetch`, and supplied Origin headers must match the API origin. Authenticated mutations additionally require `X-CSRF-Token`, obtained from login, registration or `/api/auth/me`. The browser keeps this CSRF token in memory, not localStorage. Only the active conversation ID is stored in localStorage, keyed by user ID. API responses are marked `Cache-Control: no-store`.

There are in-process limits of ten valid credential submissions per client IP per minute and 120 authenticated requests per user per minute. Forwarded IP headers are not trusted. These limits are for local use and are not a distributed abuse-prevention system.

Security references: [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), and [CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

## API

| Method and route | Body / result |
| --- | --- |
| `POST /api/auth/register` | `{email,password}` → 201 `{user:{id,email},csrf_token}` + session cookie |
| `POST /api/auth/login` | Same body → 200 session response |
| `GET /api/auth/me` | Current user and CSRF token; 401 if signed out/expired |
| `POST /api/auth/logout` | Revokes current session; 204 |
| `GET /api/conversations` | `{conversations:[{id,title,updated_at}]}` |
| `POST /api/conversations` | Creates an empty conversation; 201 `{id,title,updated_at}` |
| `GET /api/conversations/{id}/messages` | `{messages:[{id,request_id,role,content,status,created_at}]}` in display order |
| `DELETE /api/conversations/{id}` | Deletes conversation and dependent records; 204 |
| `POST /api/chat` | `{message,conversation_id,request_id}`; both IDs are UUIDs |

Chat returns `{answer,agents_used,request_id,latency_ms,conversation_id}`. The response request ID is the client idempotency ID, not a model-generated ID. A retry must reuse that ID and the exact same trimmed message and conversation. Successful retries return the saved response without invoking the model again. Reusing an ID with different input returns 409. An already-pending request returns 409 (or 503 while the shared agent is busy).

## Conversation memory and retries

The backend persists a pending user message before executing the model. On success it atomically saves the assistant message and completed response. On failure it marks the user turn failed, making it retryable. Retrying a failed turn replaces its pending user record instead of duplicating it; an older failed turn retried later moves to the end of the thread.

The concierge receives at most the six most recent successful user/assistant pairs, bounded to 16,000 characters of serialized JSON. Whole pairs are retained; a pair that exceeds the remaining budget is omitted along with older context. Failed and pending turns are excluded. The current question is supplied separately and has an 8,000-character limit.

The concierge explicitly passes `reset=True` on each execution. Specialist wrappers call `run(task)` without an explicit reset argument and rely on the library default; they do not receive the persisted history directly. The concierge uses authorized conversation context to formulate standalone specialist questions. There is no cross-conversation profile or automatic summary.

The browser uses a stable request ID when retrying a timeout or failed request. A browser timeout does not cancel work already executing on the server. Reload the thread or use Retry to check the result. When the backend lazily initializes its store after a restart, persisted pending requests are marked failed so interrupted work can be retried.

**Run one backend process/worker for this version.** The shared-agent lock, startup recovery and rate limits assume a single process. An interrupted external model request might already have incurred cost even if its result was never saved; exactly-once external billing cannot be guaranteed across crashes.

## Current limitations

No email verification, password reset, account deletion UI, MFA, automatic retention policy, automatic summary, or database encryption is implemented. Registration is open to anyone who can reach the local service. All users currently share the same example insurance-policy PDF; user-specific document ingestion is not implemented. Do not expose this prototype publicly without a separate deployment/security design.

The specialist A2A servers currently print full questions and responses to stdout. Conversation deletion does not delete these logs. Use synthetic questions in the lab; logging redaction and service authentication are still planned work. See [architecture limitations](architecture.md#evidence-observability-and-security-limits).
