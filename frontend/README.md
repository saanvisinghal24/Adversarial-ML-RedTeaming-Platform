# Frontend (M1)

React 18 + Vite + Tailwind + React Query + Zustand + Recharts + Framer Motion. Talks to the
FastAPI backend and nothing else — there is no mock data anywhere in here.

## Run it

```bash
npm install
npm run dev          # http://localhost:5173
```

The backend must be running on `http://localhost:8000`. Vite proxies `/api/*` to it in dev, so the
browser never makes a cross-origin call and CORS stays out of your way. For a deployed build, set
`VITE_API_URL` to the public API URL (see `.env.example`).

```bash
npm run build && npm run preview     # production bundle
```

## Screens

| Route | What it does |
|---|---|
| `/login` | Sign in or create an account. Tokens go to localStorage via Zustand. |
| `/models` | Upload a `.pkl` / `.onnx` / `.pt` artefact, see everything uploaded with its SHA-256. |
| `/scans/new` | Pick a model, tick attacks, tune epsilon / iterations / query budget, queue the scan. |
| `/scans/:id` | Live status polling, grade + component breakdown, per-attack ASR chart, ATLAS table, remediation checklist, PDF/HTML export. |
| `/models/:id` | Score history — trend line across scans plus the full scan list. |

Polling only runs while a scan is `queued` or `running`; React Query stops on its own once the
status settles, so an open tab isn't hammering the API.

## Design notes

- **Type:** General Sans for display (uppercase, tight leading), Inter Tight for everything else.
  Inter Tight is bundled via `@fontsource` so it's genuinely self-hosted. General Sans loads from
  Fontshare — to self-host it too, drop the woff2 files in `public/fonts/`, uncomment the
  `@font-face` block in `src/styles/index.css`, and delete the `<link>` in `index.html`.
- **Colour:** warm off-white paper `#FAFAF8`, near-black ink `#141210`, and three signal colours
  that only ever encode severity — red `#B4361E` (high), amber `#8A6A1F` (medium), moss `#3F5B43`
  (low / healthy). Colour is never decoration here.
- **Layout:** fixed left rail, content on uneven 5/7 and 4/8 splits. No card grids — findings and
  scans are rule-separated rows, which is also just easier to scan.
- **Motion:** one reveal per page load, plus a pulse while a scan is running. Everything else moves
  only when you do. `prefers-reduced-motion` turns it all off.

## Where the type scale lives

`src/styles/index.css` — `.t-display`, `.t-head`, `.t-sub`, `.t-label`, `.t-data`. Every screen uses
those classes rather than ad-hoc font sizes, which is what keeps login and the scorecard looking
like the same product.
