# CodeVerse

A developer workspace combining Git repositories, browser-based editing, AI-assisted development, API provider routing, project previews and one-click deployment.

## Current status

Initial UI scaffold. The browser interface is not yet connected to a production backend. **Do not enter real API keys until the secure backend and authentication are deployed.**

## Planned architecture

- Frontend: Next.js + TypeScript + Tailwind CSS + Monaco Editor.
- API: FastAPI; all provider calls are proxied server-side.
- Database/auth: PostgreSQL + Supabase Auth (or equivalent).
- Secrets: encrypted server-side secret storage; never commit secrets or expose them to browser JavaScript.
- Deployment: Vercel for frontend, a protected backend host for API, custom domains via DNS.

## Security rules

1. Never put provider keys in frontend code, localStorage, sessionStorage, URLs, or Git history.
2. Store only encrypted secrets on the server; show masked values in the admin UI.
3. Enforce admin authorization server-side on every key/provider endpoint.
4. Use environment variables for encryption keys and service credentials.
5. Rotate any key that was accidentally exposed.

## Development

The initial landing page is static. Backend integration, login, repository operations, provider adapters, billing, and deployment workflows are subsequent milestones.
