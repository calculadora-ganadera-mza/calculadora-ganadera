API y motor de cálculo en Python.

## Authentication

Configure these variables in the root `.env` (see `.env.example`):

- `JWT_SECRET_KEY`: at least 32 random characters; generate with `openssl rand -hex 32`.
- `AUTH_ALLOWED_ORIGINS`: JSON array of trusted frontend origins, e.g. `["http://localhost:5173"]`.
- `AUTH_COOKIE_SECURE`: `false` for local HTTP only; use `true` with HTTPS in production.
- `ACCESS_TOKEN_MINUTES`: defaults to 15.
- `REFRESH_TOKEN_DAYS`: defaults to 7. Rotation preserves the original session deadline.

Run `uv sync`, then `uv run alembic upgrade head` with the database environment
configured before starting the API. With Docker, run
`docker compose exec backend alembic upgrade head` after rebuilding the backend.

`POST /auth/login` accepts OAuth2 form fields `username` (email) and `password`.
`POST /auth/register` accepts JSON `name`, `email`, `password`.
Both return an access JWT and set an HttpOnly refresh cookie. Browser POSTs to
auth endpoints must include an Origin from the allowlist (also for API clients
and Swagger's Try it out; add the docs origin explicitly if needed).
`POST /auth/refresh` rotates that cookie and returns a new access JWT.
`POST /auth/logout` revokes the entire current refresh family and clears the cookie.
`GET /auth/me` is an example protected endpoint using the Bearer access JWT.
Logout does not invalidate already-issued access JWTs before their expiry.
Consumed tokens are retained to detect reuse; do not remove them before the
family expires. Different logins create independent families.

The Vue client restores its session on startup and provides `login`, `register`,
`logout`, and `authenticatedFetch` in `src/api/auth.ts`. Use `authenticatedFetch`
for protected API calls (relative paths such as `/auth/me`). It retries once after
a 401 and redirects to `/login` if renewal fails. Access JWTs stay in memory.
The current app has no protected product routes; adding auth does not restrict
its public calculator pages. The account form is at `/login`.

The default cookie uses SameSite=Lax and supports same-site deployments, including
the existing `/api` proxy. Deploying frontend and API on different sites requires
reviewing SameSite=None, HTTPS, and third-party cookie restrictions. Keep the
explicit Origin checks. Token responses must never be cached by a reverse proxy.
