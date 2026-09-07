# Optional: inspect model calls with Langfuse

[Setup](SETUP.md) · [Facilitator notes](SPEAKER_NOTES.md)

Langfuse records model calls and checklist scores so you can inspect a run afterward. The workshop works without it: leave `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` empty in the repository's `.env`.

Set this up before the event if you plan to show it. Docker startup and trace ingestion can take time.

## 1. Prepare the local stack

Install/start Docker Desktop, or Docker Engine with Compose. This repo includes a Compose file in `docker/langfuse/`; **its `.env` is not included in Git**. From the repository folder, create a local file if one is not already present:

```bash
# From the checkout containing pyproject.toml.
chmod +x scripts/start-langfuse.sh scripts/stop-langfuse.sh
./scripts/start-langfuse.sh
```

This creates application secrets and leaves the Compose file's other local-demo defaults in place. The bundled stack publishes ports 3000 and 9090 on all host interfaces; keep it on a trusted local machine. Shared hosting needs its own credentials and network configuration.

## 2. Start and sign in

```bash
cd docker/langfuse
if [[ ! -f .env ]]; then cp .env.example .env; fi
docker compose --env-file .env up -d
```

On Windows PowerShell, use `if (-not (Test-Path .env)) { Copy-Item .env.example .env }` before the same `docker compose` command.

Open <http://localhost:3000> after the services are healthy. Create a local account and project, then create project API keys. If an existing Docker `.env` supplies `LANGFUSE_INIT_*` values, use the account/project it initializes instead.

The start script creates the missing Docker `.env` from the checked-in local
demo template. Existing environments are preserved. All exposed ports bind to
localhost; these sample credentials are for a local workshop only.

## Wire ParcelCo

**There is no guaranteed shared workshop login.** Create a local LangFuse project and paste its keys into the repo `.env`. Sample credentials in scripts are for local Docker only.

## 3. Connect ParcelCo

In the repository-root `.env` (a different file from the Docker `.env`), set:

```dotenv
LANGFUSE_PUBLIC_KEY=replace-with-your-project-public-key
LANGFUSE_SECRET_KEY=replace-with-your-project-secret-key
LANGFUSE_HOST=http://localhost:3000
```

Restart ParcelCo:

```bash
python -m parcelco.cli serve --suite demo
```

Run one ticket, then open its trace link. Compare the recorded generations with the attempt trail and inspect the checklist scores. Langfuse verifies recorded workflow evidence; it is not the policy grader. Do not promise every graph node has its own span: callbacks are attached to the generation calls.

## If a trace is missing

- Confirm both keys belong to the same project and the host matches your local server.
- Wait briefly for ingestion, then refresh the trace. The app can report pending evidence before it appears.
- Check the services and logs:

```bash
docker compose --env-file docker/langfuse/.env -f docker/langfuse/docker-compose.yml ps
docker compose --env-file docker/langfuse/.env -f docker/langfuse/docker-compose.yml logs --tail 80 langfuse-web langfuse-worker
```

If tracing is distracting from the lesson, empty both keys in the root `.env`, restart ParcelCo, and continue with the dashboard's local results.

## Stop

```bash
docker compose --env-file docker/langfuse/.env -f docker/langfuse/docker-compose.yml down
```

This stops the stack and retains named volumes. ParcelCo's **Reset memory** clears its own local history, not these Langfuse records.
