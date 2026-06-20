# Session Timeout Design

## Scope

This document defines the recommended session timeout model for the shared browser authentication used by:

- `idounAIChat` as the auth issuer and session owner
- `technews-publisher` as a relying application that validates the same cookie

It is written from the `technews` feature request context, but the implementation boundary lives primarily in `idounAIChat/backend/app/api/routes_auth.py` and related auth/session code.

## Current behavior

As of 2026-06-20, the shared login flow behaves like this:

- login issues a single JWT cookie named `idounai_session`
- token expiry is controlled by `access_token_expire_minutes`
- current default is `60 * 24`, which is 24 hours
- `GET /api/auth/session` refreshes the token and resets the cookie expiry on every successful check
- `technews-publisher` does not issue its own session; it only verifies the shared cookie

In practice this is a sliding single-token session that can remain active indefinitely while the browser keeps making authenticated requests.

## Goals

- Keep normal reading and favorites usage comfortable
- Avoid effectively permanent browser sessions
- Support explicit idle timeout and absolute expiry
- Preserve shared login across `idounAIChat` and `technews`
- Leave room for per-device logout and session inspection later

## Recommended policy

### Timeout values

- Idle timeout: 30 minutes
- Absolute session lifetime: 7 days
- Default login lifetime without "keep me signed in": session cookie or at most 12 hours
- Optional "keep me signed in" lifetime: 7 days

### Why these values

- 30 minutes is a common web-app idle timeout and is not too disruptive for a read-heavy product
- 7 days prevents a never-ending sliding session while still feeling convenient on personal devices
- The product is not a banking or admin-console workflow, so stricter values like 10 to 15 minutes would likely hurt UX more than they help

## Target model

Move from a single endlessly refreshed access JWT to a two-layer model:

- short-lived access token for request authentication
- longer-lived refresh/session token backed by a server-side session record

### Token model

- Access token:
  - HttpOnly cookie
  - lifetime: 30 minutes
  - used directly by APIs
- Refresh/session token:
  - HttpOnly cookie
  - lifetime: 7 days
  - mapped to a DB session row
  - rotated or re-issued during refresh depending on implementation preference

## Session record

Add a persistent session table in `idounAIChat` to own browser sessions.

Suggested table: `user_sessions`

Suggested columns:

- `id`
- `user_id`
- `refresh_token_hash`
- `created_at`
- `last_activity_at`
- `expires_at`
- `revoked_at`
- `user_agent` nullable
- `ip_address` nullable

### Column intent

- `last_activity_at` enforces idle timeout
- `expires_at` enforces absolute expiry
- `revoked_at` supports logout and future per-device revocation
- `refresh_token_hash` avoids storing the raw refresh token

## Request flow

### Login

1. Verify credentials.
2. Create a `user_sessions` row.
3. Issue:
   - access token cookie with 30-minute expiry
   - refresh token cookie with 7-day expiry

### Normal authenticated request

1. If the access token is valid, allow the request.
2. If the access token is close to expiry, optionally rotate it quietly.
3. Do not extend the session forever without checking server-side session limits.

### Refresh path

1. If the access token is expired, inspect the refresh token.
2. Resolve the session row from the refresh token hash.
3. Reject if:
   - the session is revoked
   - `now - last_activity_at > 30 minutes`
   - `now > expires_at`
4. If still valid:
   - update `last_activity_at`
   - issue a fresh access token
   - optionally rotate the refresh token too

### Logout

1. Revoke the `user_sessions` row.
2. Clear both access and refresh cookies.

## Behavior in shared auth

Because `technews-publisher` relies on `idounAIChat` auth:

- timeout policy must be implemented in the auth owner first
- `technews-publisher` should continue validating the auth cookie but should not invent a second independent session system
- any new refresh endpoint or session schema should be shared by both apps

This keeps browser auth consistent and avoids cases where one app silently stays signed in longer than the other.

## Frontend behavior

### Expected UX

- if the user returns after more than 30 minutes of inactivity, the next protected request should fail cleanly and trigger re-login
- if the user is actively browsing within the allowed session window, silent refresh should keep the experience smooth
- if the absolute 7-day lifetime is reached, require full re-authentication

### Technews-specific UX

For `technews`, the UI should stay lightweight:

- show a simple message such as `세션이 만료되어 다시 로그인해 주세요.`
- preserve the current issue page, selected article, and scroll target when possible
- after re-login, restore the user to the same place

This is preferable to an aggressive blocking modal because `technews` is mostly a read-and-save flow.

## Why not keep the current single-token model

The current model is simple, but it has several weaknesses:

- successful session checks effectively extend the login forever
- there is no real absolute expiry
- per-device logout is awkward
- session audit and future session management are limited
- revocation is weaker because session ownership is mostly in the cookie itself

## Minimal alternative

If a fast interim patch is needed before the full session table work, a reduced version is possible:

- shrink the JWT lifetime to 30 minutes
- stop refreshing it on every `/api/auth/session` call
- require manual re-login on expiry

This is simpler to ship, but it is intentionally a stopgap because it lacks:

- absolute session lifetime
- device/session records
- clean revocation semantics
- future "log out other devices" support

## Recommended rollout

### Phase 1

- add `user_sessions`
- add refresh token cookie support
- keep access token at 30 minutes
- enforce 30-minute idle timeout and 7-day absolute expiry
- update `/api/auth/session` semantics to use session-backed refresh behavior

### Phase 2

- add "keep me signed in" option in the login UI
- add per-device session list
- add "log out all other sessions"
- add recent login metadata if useful

## Implementation notes

### Likely files to change in `idounAIChat`

- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/api/routes_auth.py`
- new session model under `backend/app/models/`
- auth dependency code that resolves the current user

### Likely files to adjust in `technews-publisher`

- `frontend/lib/api.ts`
- `frontend/components/technews-shell.tsx`

These changes should mainly be about handling session expiry and re-auth flow more gracefully, not about owning auth policy.

## Final recommendation

Adopt:

- 30-minute idle timeout
- 7-day absolute session lifetime
- shared access-token plus refresh-token model
- DB-backed `user_sessions` ownership in `idounAIChat`

This gives `technews` a normal modern web-app session behavior without making the reading flow annoyingly fragile.
