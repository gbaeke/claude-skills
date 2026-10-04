# Frontend

## Why a SPA served by FastAPI (not Next.js)

With a Python backend, a Vite SPA built into `frontend/dist` and served by FastAPI is **one image, one runtime, one
origin**: no CORS, no second container, one port. FastAPI serves real files from `dist/` and `index.html` for every
other non-API path (deep links work). Next.js only earns its second runtime with public, SEO-relevant pages that need
server rendering. Don't add it for apps behind a sign-in.

In development, `scripts/run-local.sh --dev` runs Vite on :5173 with hot reload, proxying `/api` (and `/auth`) to
the backend on :8000.

## Stack

React 19, TypeScript 6 (strict, `noUncheckedIndexedAccess`; on 7 see "Freshness" in SKILL.md), Vite,
`react-router` (the package; `react-router-dom` is the legacy name) in declarative mode, TanStack Query, Tailwind v4,
lucide icons, sonner toasts.

## The API client is generated, never written

`npm run gen:api` exports the backend's OpenAPI (`python -m <pkg>.openapi`, no server needed) and runs
`@hey-api/openapi-ts`, configured in `openapi-ts.config.ts`, into `src/client/`. That gives types (`NoteOut`), an
SDK, and TanStack Query helpers: `listNotesOptions()`, `listNotesQueryKey()`, `createNoteMutation()`. Commit
`src/client/`. `check.sh` regenerates it and fails when it was stale, so a backend change without a regenerated
client never passes. Prettier and oxlint skip it. `lib/api.ts` configures the client once (`setupApiClient()` in
`main.tsx`), and every failure becomes an `ApiError` (code, message, status). With auth, a 401 sends the browser to
the sign-in.

hey-api is what the official FastAPI full-stack template uses. It is 0.x, so `^0.N` keeps it on one minor; read its
changelog before moving to the next. The alternative is `openapi-typescript` + `openapi-fetch`, which works but
declares a TypeScript 5 peer and forces `--legacy-peer-deps`.

## Data and state

- Server data goes through TanStack Query with the generated options:
  `useQuery(listNotesOptions())`, `useMutation({ ...createNoteMutation(), onSuccess: () =>
  qc.invalidateQueries({ queryKey: listNotesQueryKey() }) })`. Never `useEffect` + `fetch`.
- UI state stays in `useState` near where it's used. Add a store only once several distant components share client
  state, which is rare when server state lives in TanStack Query.
- Layout: `pages/` (one per screen, routes in `main.tsx`), `components/` (shared), `lib/`. Put a component used by one
  page next to that page or inside it.

## Styling

Design tokens are CSS variables in `index.css`, defined for light (`:root`) and dark (`.dark`) and exposed to
Tailwind through `@theme inline` (`bg-surface`, `text-fg-muted`, `border-border`, `bg-accent` ...). Components use
token classes, never raw colours, so a rebrand touches only this file. Text keeps WCAG AA contrast in both themes.
Repeated patterns (`card`, `btn-primary`, `btn-ghost`, `input`) are Tailwind v4 `@utility` classes; anything used
once stays inline. `cn()` (clsx + tailwind-merge) composes conditional classes. The theme toggle (system, light,
dark) is remembered in localStorage.

**Brand:** to apply a brand, change the token values. For MbarQ, the extractor app's palette is: off-black `#1e1e1e`,
warm off-white `#f9f7f2`, purple `#826aed` (a deeper `#6a4fe0` for text and buttons in light mode, `#a594f4` in dark,
for AA contrast), neon `#e6ff2b` (decoration only), Poppins for headings, Inter for text, pill buttons, 16px cards.

## Lint, format, tests

- **oxlint** (correctness as errors, suspicious as warnings, `--deny-warnings`), with `react-hooks` and
  `import/no-cycle`. **Prettier** formats (no semicolons, single quotes, 120 columns). oxfmt is still beta.
  `tsc -b` in the build is the type check.
- **Tests:** none by default. Add **Vitest** once the frontend has logic worth testing (parsing, formatting,
  reducers), and one **Playwright** smoke test (sign in, open the main screen, do the main action) once the app has a
  critical path. Run both from `check.sh`.
