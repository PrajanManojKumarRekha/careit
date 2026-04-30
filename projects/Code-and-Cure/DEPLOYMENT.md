# Deployment

This repo is set up for:

- `Vercel` for the Next.js frontend in `src/frontend`
- `Render` for the FastAPI backend at the repo root

## Vercel

Create a Vercel project with:

- Root Directory: `src/frontend`
- Framework Preset: `Next.js`

Set these environment variables in Vercel:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-render-service.onrender.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_CLERK_TOKEN_TEMPLATE=careit-api
NEXT_PUBLIC_ENABLE_DEMO_AUTH=true
```

If you use a custom frontend domain, add that domain to the backend `CORS_ORIGINS`.

## Render

The repo includes a [render.yaml](./render.yaml) Blueprint for the API service.

Required environment variables on Render:

```env
APP_ENV=production
ALLOW_DOTENV=false
ALLOW_ONEDRIVE_DOTENV=false
ALLOW_DEMO_MODE=true
JWT_COOKIE_SECURE=true
JWT_COOKIE_SAMESITE=none
JWT_SECRET_KEY=<long-random-secret>
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=<supabase-service-key>
CLERK_SECRET_KEY=sk_live_...
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json
CLERK_JWT_ISSUER=https://your-clerk-domain.clerk.accounts.dev
CLERK_JWT_AUDIENCE=
CLERK_API_URL=https://api.clerk.com
CLERK_TOKEN_TEMPLATE=careit-api
AUTH_EMAIL_DELIVERY_MODE=smtp
AUTH_EMAIL_FROM=no-reply@your-domain.com
SMTP_HOST=<smtp-host>
SMTP_PORT=587
SMTP_USERNAME=<smtp-username>
SMTP_PASSWORD=<smtp-password>
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

Set CORS and host policy for your deployed domains:

```env
CORS_ORIGINS=https://your-frontend.vercel.app,https://your-custom-frontend-domain.com
CORS_ORIGIN_REGEX=^https://.*\\.vercel\\.app$
ALLOWED_HOSTS=your-render-service.onrender.com,your-api-domain.com
```

`CORS_ORIGIN_REGEX` is optional, but useful if you want Vercel preview deployments to call the API without updating `CORS_ORIGINS` every time.

## Production Guardrails

In `APP_ENV=production`, the API now fails fast if:

- required secrets are missing or still placeholder values
- `JWT_COOKIE_SAMESITE=none` is used without `JWT_COOKIE_SECURE=true`
- `CORS_ORIGINS` only contains localhost values and no `CORS_ORIGIN_REGEX` is set
- `ALLOWED_HOSTS` only contains localhost values
- demo mode is enabled without a real `JWT_SECRET_KEY`

This keeps the deployed service from booting with an insecure or incomplete configuration.
