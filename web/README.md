# Web dashboard

Next.js frontend for the Used Vehicle Acquisition IDSS. It calls the FastAPI
backend and renders the Buy/Pass recommendation, price comparison, financials,
and confidence breakdown.

## Develop

```bash
npm install
npm run dev
```

Open http://localhost:3000. The backend must be running (default
http://localhost:8000); see the root `README.md` for the full setup.

Point the app at a different API with `NEXT_PUBLIC_API_BASE` in `.env.local`.

## Structure

- `src/app/page.tsx`: landing page
- `src/app/app/page.tsx`: the evaluation tool
- `src/components/`: UI cards (verdict, price comparison, summaries, input rail)
- `src/lib/api.ts`: typed client for the backend
