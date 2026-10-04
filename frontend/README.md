# Rocket Forensics — Frontend (Team Rocket · SIH prototype)

React + Vite + TypeScript + Tailwind + React Router + Framer Motion + Three.js (@react-three/fiber, drei).

## Run
```bash
npm install
cp .env.example .env    # set VITE_API_BASE_URL (default http://localhost:8000)
npm run dev             # http://localhost:5173
npm run build           # type-check + production build
```

## IMPORTANT — verify before demo
This project was written without network access, so `npm install` / `npm run build` were **not run**.
Run them first and fix any type errors (expected to be few, mostly in `src/api/normalize.ts` if your backend shapes differ).

## Backend contract assumed (edit only `src/api/*`)
| Purpose | Endpoint |
|---|---|
| Register / login (JSON, returns `access_token`) / me | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Cases | `GET/POST /api/cases`, `GET /api/cases/{id}` |
| Evidence | `GET/POST(multipart "file") /api/cases/{id}/evidence`, `GET /api/evidence/{id}`, `POST /api/evidence/{id}/verify` |
| Stream | `GET /api/evidence/{id}/stream` (Range support; accepts `?access_token=` — otherwise player falls back to an authenticated blob download) |
| Analysis | `POST /api/evidence/{id}/analyze`, `GET .../analysis`, `.../detections`, `.../motion-events`, `.../snapshots`, `.../device` |
| Case data | `GET /api/cases/{id}/timeline`, `/search?object=&camera=&start=&end=&event_type=`, `/correlation`, `/custody` |
| Reports | `GET/POST /api/cases/{id}/reports`, `GET /api/reports/{id}/download` |

If FastAPI's login uses OAuth2 form data (`username`/`password`), change `src/api/auth.ts`.
Field-name differences are absorbed in `src/api/normalize.ts` (accepts common aliases: `_id`, `sha256_hash`, `bbox` as array/object, etc.).
Snapshot images are loaded with `?access_token=` because `<img>`/`<video>` cannot send headers.

## Notes
- No mock data. Empty/absent data renders "NO DATA AVAILABLE"; backend down renders "BACKEND OFFLINE".
- Progress is shown only if the backend returns frame counts; otherwise "PROCESSING…".
- Correlation is labelled "TEMPORALLY CORRELATED" only (no identity claims).
- 3D network falls back to 2D on weak devices, no WebGL, or reduced-motion.
- `npm run lint` = `tsc --noEmit` (no ESLint configured).
