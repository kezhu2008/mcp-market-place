# Frontend

Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui-style primitives.

## Local dev

```bash
pnpm install
cp .env.example .env.local      # fill in Cognito + API values
pnpm dev
```

## Env

- `NEXT_PUBLIC_API_BASE_URL` — FastAPI base URL (API Gateway).
- `NEXT_PUBLIC_COGNITO_USER_POOL_ID`
- `NEXT_PUBLIC_COGNITO_CLIENT_ID`
- `NEXT_PUBLIC_COGNITO_DOMAIN`
- `NEXT_PUBLIC_COGNITO_REDIRECT_URI`

Without these set, pages render but API calls will fail — useful for UI-only dev.

## Scripts

- `pnpm lint` — ESLint
- `pnpm typecheck` — `tsc --noEmit`
- `pnpm test` — Vitest
- `pnpm build` — Production build
