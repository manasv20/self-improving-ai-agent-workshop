# Self-host Langfuse with Docker

Langfuse is MIT open source. This workshop vendors the official compose stack under `docker/langfuse/`.

## Start

```bash
cd ~/Desktop/Self\ Improving\ AI\ Agent\ Workshop
chmod +x scripts/start-langfuse.sh scripts/stop-langfuse.sh
./scripts/start-langfuse.sh
```

Or:

```bash
cd docker/langfuse
docker compose --env-file .env up -d
```

UI: **http://localhost:3000**  
Login: `workshop@parcelco.local` / `WorkshopDemo1!`

## Wire ParcelCo

In the **repo root** `.env`:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-workshop-aa8504fbeda3a221cb5d6a06dd9bd83c
LANGFUSE_SECRET_KEY=sk-lf-workshop-4bfad518fa4844a0a79e1d3cd0585409
LANGFUSE_HOST=http://localhost:3000
```

Then restart the Flask app:

```bash
source .venv/bin/activate
python -m parcelco.cli serve
```

On the dashboard:

- Stack step **LangFuse** shows connected / Tracing ON when keys + auth work  
- **LangFuse traces** panel lists recent ticket traces with **Open trace** links  
- **Open LangFuse** opens the UI; inspector links to that run’s trace  

(Langfuse sets `X-Frame-Options: SAMEORIGIN`, so the full UI opens in a tab rather than an iframe.)

## Stop

```bash
./scripts/stop-langfuse.sh
```

## Notes

- Needs Docker Desktop (or Docker Engine + Compose v2).
- First boot pulls several images (web, worker, postgres, clickhouse, redis, minio) — can take a few minutes.
- Workshop secrets in `docker/langfuse/.env` are fine for local demos; rotate before any shared/networked deploy.
- Host ports used: **3000** (UI), **9090** (minio), plus localhost-only DB ports.
