# Gridfinity Cutout Generator — Frontend

Minimal Next.js (App Router, TypeScript) UI that talks to a FastAPI backend.

## Features
- Identify item → auto-fill dimensions (via `/identify` + `/dimensions`).
- Generate proposals (`/proposals`) and pick one.
- Generate STL (`/stl`) and preview it in a Three.js viewer.
- Tailwind styling, lightweight deps.
- Configurable API base via `NEXT_PUBLIC_API_BASE`.

## Getting Started
```bash
cd frontend
cp .env.local.example .env.local  # update if your API isn't localhost:8000
npm install
npm run dev
```

Then open http://localhost:3000 and try the **Demo** button if your backend isn't ready yet.
