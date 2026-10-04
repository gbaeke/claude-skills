# Sign-in with WorkOS AuthKit (optional module)

Auth is **off unless asked for**. Even when installed, it only activates with `WORKOS_CLIENT_ID` set; without it the
app runs open (locally, that's fine).

## How it works

`auth.py` uses WorkOS's **sealed sessions** (the session helpers in the Python SDK):

1. `/auth/login` stores a random `state` in a short cookie and redirects to AuthKit's hosted page.
2. `/auth/callback` checks the state, trades the code for tokens (`authenticate_with_code`), seals access token +
   refresh token + user with `SESSION_SECRET` (`seal_session_from_auth_response`) into the httponly, `SameSite=Lax`
   `wos_session` cookie (`Secure` on https), and redirects to `next`. `next` is limited to paths on this site.
3. Each request: `AuthMiddleware` (plain ASGI) loads the sealed session and verifies the access token locally
   (signature and expiry, against WorkOS's cached JWKS). Once it expires (minutes), it calls `refresh()` and writes
   the new cookie into the response. Refresh fails once WorkOS has ended the session (signed out elsewhere, user
   removed, session length set in the dashboard), so revocation works. The previous design, a home-grown cookie
   valid for N hours, couldn't do that.
4. Signed out: `/api/*` answers 401 in the error envelope (the frontend redirects to sign-in), and pages redirect to
   `/auth/login?next=...`. `/auth/*` and `/api/health` stay open (the health probe).
5. `/auth/logout` clears the cookie and goes through WorkOS's logout URL, so the WorkOS session ends too.
6. `ALLOWED_USERS` (optional) is a second, app-side list of emails, checked at sign-in and on every request.

`request.state.user` holds the `User` (id, email), and `GET /api/me` returns it (null when sign-in is off). Tests use
`FakeWorkOS` through the `WorkOSAuth` protocol and never call WorkOS.

**CSRF:** `SameSite=Lax` plus no state-changing GET endpoints. Keep it that way: changes go through
POST/PUT/PATCH/DELETE.

## The WorkOS CLI (needed for this module)

Install with `npm install -g workos`. Sign in with `workos auth login`; the user runs it, so suggest `! workos auth
login`. Check with `workos auth status --mode agent` (JSON, `authenticated: true`). Useful commands, always with
`--mode agent` for JSON:

- `workos project list`: environments with their `clientId` and `id`.
- `workos authkit redirect-uris list|set --environment-id <id>` and `workos authkit logout-uris list|set`. `set`
  replaces the whole list, so use `scripts/workos-uris.sh add|remove <app url>`, which merges and keeps the default.
- `workos user list`, `workos user get|update|delete <id>`: who can sign in (with sign-up off in the dashboard, users
  are created there or invited).
- `workos doctor`: diagnoses the AuthKit integration in the current project. `workos verify-login` tests the sign-in
  loop end to end with a throwaway user.

## Setup

1. Pick or create the environment (`workos environment list`, `workos environment use`). Note its client id, and get
   an API key (dashboard: API Keys).
2. In `.env` (never in the chat): `WORKOS_CLIENT_ID`, `WORKOS_API_KEY`, `SESSION_SECRET` (`openssl rand -base64 32`;
   changing it signs everyone out), and optionally `ALLOWED_USERS`.
3. Run `WORKOS_CLIENT_ID=... scripts/workos-uris.sh add http://localhost:8000`, and the same for `:5173` when using
   `--dev`. In the dashboard: sign-up off if only invited people may enter, and sign-in endpoint `<app>/auth/login`.
4. On Azure: `WORKOS_CLIENT_ID=... WORKOS_API_KEY=... scripts/azure-deploy.sh` stores them in the deployment state
   (`.azure/<rg>.env`). `SESSION_SECRET` is generated. The app's https address is added in WorkOS automatically, and
   `PUBLIC_URL` is set, because behind the ingress the app sees http. `WORKOS_CLIENT_ID= scripts/azure-deploy.sh`
   turns sign-in off again.
