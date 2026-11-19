# CRATE-SCAN frontend (Next.js)

Next.js 16 (App Router) · React 19 · TypeScript strict · Tailwind CSS 4 (design tokens in `src/app/globals.css`) · Firebase Web SDK
(Google sign-in) · pnpm.

## Run locally

```bash
cd frontend
cp .env.example .env.local      # set NEXT_PUBLIC_* values (browser-safe only)
pnpm install
pnpm dev                        # http://localhost:3000
```

For local work without a Firebase project use the Auth emulator: set `NEXT_PUBLIC_USE_AUTH_EMULATOR=true`,
`NEXT_PUBLIC_FIREBASE_PROJECT_ID=demo-cratescan`, `NEXT_PUBLIC_FIREBASE_API_KEY=demo-api-key` and run the backend with the emulator too
(see `backend/README.md`). Demo data: `cd backend && uv run python -m scripts.dev_seed`.

## Scripts

| Command                                              | Purpose                                                                          |
| ---------------------------------------------------- | -------------------------------------------------------------------------------- |
| `pnpm typecheck` / `pnpm lint` / `pnpm format:check` | Static checks                                                                    |
| `pnpm test`                                          | Vitest unit/component tests                                                      |
| `pnpm build` / `pnpm start`                          | Production build / serve                                                         |
| `pnpm e2e`                                           | Playwright (needs backend :8000, Auth emulator :9099, seeded data, app on :3000) |
| `pnpm gen:api`                                       | Regenerate `src/lib/api-types.ts` from `backend/openapi.json`                    |
| `pnpm gen:icons`                                     | Regenerate icons from `design/assets/icons`                                      |

## Structure

`src/app` routes (public, `/inspector/*`, `/admin/*`) · `src/components` design-system components (`ui`, `shell`, `inspection`, `report`,
`media`, `charts`, `reference-form`) · `src/lib` (`api` typed client with token refresh + cold-start retry, `auth` context and route guards,
`firebase`, `env`). The backend enforces every permission; client guards are only for navigation.
