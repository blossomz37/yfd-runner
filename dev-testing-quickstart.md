From the repo root, run:

```bash
cd web
npm run dev -- --hostname 127.0.0.1 --port 3001
```

Then open:

```text
http://127.0.0.1:3001
```

If you want the frontend to talk to the FastAPI backend instead of fallback data, start the backend in another terminal from the repo root:

```bash
source .venv/bin/activate
uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```

The frontend already defaults to `http://127.0.0.1:8000` via `YFD_STUDIO_API_BASE`, so you usually don’t need to set anything extra.