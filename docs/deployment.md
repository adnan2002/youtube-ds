# Deployment Strategy

This project should be deployed as a low-cost open-source data application:

- React/Vite frontend with static assets.
- FastAPI backend for deterministic data endpoints and AI-assisted endpoints.
- Read-only SQLite database generated from the cleaned dataset.
- External LLM API calls, so production compute needs are light.

Pricing and limits below were checked on 2026-07-09. Re-check before launch because free tiers change.

## Recommended Cheapest Architecture

Use an Oracle Cloud Infrastructure Always Free VM with Docker Compose, Cloudflare DNS, and Caddy as the reverse proxy.

```text
User browser
  |
  v
Cloudflare DNS/CDN/TLS
  |
  v
OCI Always Free VM
  |-- Caddy reverse proxy
  |-- static React build
  `-- FastAPI container
        |-- read-only SQLite file
        `-- outbound HTTPS calls to LLM API provider
```

Why this is the default recommendation:

- It can run the existing Python/FastAPI backend without porting it to a serverless JavaScript runtime.
- The database is static, so no managed database is needed.
- Docker keeps the deployment reproducible for contributors.
- Monthly infrastructure cost can be `$0` if the deployment stays inside OCI Always Free limits.
- There is no idle spin-down cold start like many free PaaS web services.

Primary tradeoff: this is a small self-managed VM. You own OS updates, Docker updates, firewall rules, backups of any generated artifacts, and basic monitoring.

## Cost Snapshot

| Option | Expected monthly cost | Fit | Notes |
| --- | ---: | --- | --- |
| OCI Always Free VM + Docker Compose | `$0` | Best cost-effective path for the current FastAPI app | Oracle lists Always Free compute and 200 GB block volume storage, but free capacity can be region-dependent and idle instances can be reclaimed. |
| Cloudflare Pages + Cloudflare Workers + D1 | `$0` at low usage | Cheapest fully serverless path | Requires porting API endpoints from FastAPI/Python to Workers/Pages Functions. D1 is SQLite-compatible but not a raw local `.db` file at runtime. |
| Cloudflare Pages + Render Free FastAPI | `$0` for demos | Easiest managed demo | Render Free web services spin down after 15 minutes idle, take about a minute to wake, have 750 free instance hours/month, and use an ephemeral filesystem. Good for previews, not production. |
| Fly.io, Railway, Render paid, DigitalOcean, Hetzner VPS | Usually `$4-8+/mo` minimum | Paid fallback | Simpler or more predictable depending on provider, but not cheaper than the free options. |

Useful references:

- Cloudflare Pages Free: `https://pages.cloudflare.com/`
- Cloudflare Workers limits: `https://developers.cloudflare.com/workers/platform/limits/`
- Cloudflare D1 limits: `https://developers.cloudflare.com/d1/platform/limits/`
- Cloudflare D1 SQLite import: `https://developers.cloudflare.com/d1/best-practices/import-export-data/`
- Render Free instances: `https://render.com/docs/free`
- OCI Always Free resources: `https://docs.oracle.com/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm`

## Deployment Target

Use one small Linux VM:

- Ubuntu LTS or Oracle Linux.
- Docker Engine and Docker Compose plugin.
- Caddy for TLS and reverse proxy.
- One FastAPI container.
- One static frontend directory served by Caddy.
- No managed database.

Suggested public routes:

| Route | Service |
| --- | --- |
| `/` | React frontend |
| `/assets/*` | React static assets |
| `/api/*` | FastAPI backend |
| `/health` | backend health check or Caddy synthetic response |

Keep LLM credentials only on the server as environment variables. The frontend should call backend AI endpoints, never the LLM provider directly.

## SQLite Strategy

Treat SQLite as an immutable deployment artifact.

1. Build `data/youtube.db` from cleaned data in a local script or CI job.
2. Add all indexes needed by dashboard filters and AI SQL questions.
3. Run `ANALYZE` before packaging the database.
4. Package the `.db` file into the backend image or mount it read-only.
5. Open it in read-only immutable mode from the backend:

```python
sqlite3.connect(
    "file:/app/data/youtube.db?mode=ro&immutable=1",
    uri=True,
    check_same_thread=False,
)
```

Recommended production rules:

- Do not write to SQLite in production.
- Do not run migrations against the production database.
- Rebuild and redeploy the full database when the dataset changes.
- Keep the database below normal Git hosting limits if committed. If it grows large, publish it as a release artifact or download it during image build from an open dataset URL.
- Create explicit allowlisted query templates for public endpoints. For natural-language SQL, constrain the agent to `SELECT` statements and enforce a row limit.

## Docker Layout

Add Docker files when the app has real endpoints and data paths:

```text
youtube-ds/
|-- Dockerfile.backend
|-- docker-compose.yml
|-- Caddyfile
|-- backend/
|-- frontend/
`-- data/
    `-- youtube.db
```

Backend image responsibilities:

- Install `backend/requirements.txt`.
- Copy `backend/` and the read-only SQLite artifact.
- Run Uvicorn on `0.0.0.0:8000`.
- Expose no database ports.

Frontend build responsibilities:

- Run `npm ci`.
- Run `npm run build`.
- Copy `frontend/dist/` into the Caddy image or onto the VM.

Example `docker-compose.yml` shape:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      SQLITE_PATH: /app/data/youtube.db
      LLM_PROVIDER: ${LLM_PROVIDER}
      LLM_API_KEY: ${LLM_API_KEY}
    volumes:
      - ./data/youtube.db:/app/data/youtube.db:ro
    restart: unless-stopped

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./frontend/dist:/srv:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

Example `Caddyfile`:

```caddyfile
example.com {
  encode zstd gzip

  handle /api/* {
    reverse_proxy backend:8000
  }

  handle {
    root * /srv
    try_files {path} /index.html
    file_server
  }
}
```

## CI/CD

Use GitHub Actions because it is free for public repositories and familiar to open-source contributors.

Recommended workflow:

1. On pull request:
   - Install frontend dependencies with `npm ci`.
   - Run `npm run build`.
   - Install backend dependencies.
   - Run backend tests once they exist.
   - Optionally smoke-test that SQLite opens in read-only mode.
2. On push to `main`:
   - Build frontend.
   - Build backend Docker image.
   - Push image to GitHub Container Registry.
   - SSH into the VM.
   - Pull the latest image.
   - Run `docker compose up -d`.
   - Run a health check.

Keep deployment secrets in GitHub Actions secrets:

- `OCI_HOST`
- `OCI_SSH_USER`
- `OCI_SSH_KEY`
- `LLM_API_KEY`
- `LLM_PROVIDER`

Do not commit `.env`, private keys, or provider API keys.

## VM Bootstrap

High-level setup for the OCI VM:

1. Create an Always Free eligible Linux VM.
2. Open inbound ports `22`, `80`, and `443` in the OCI security list.
3. Point the domain's DNS records to the VM using Cloudflare DNS.
4. Install Docker and the Compose plugin.
5. Clone the repository.
6. Create `/opt/youtube-ds/.env` with secrets.
7. Build the frontend and start Compose:

```bash
cd /opt/youtube-ds
cd frontend && npm ci && npm run build && cd ..
docker compose up -d --build
```

8. Confirm:

```bash
curl -f https://example.com/
curl -f https://example.com/api/
```

## Runtime Configuration

Use environment variables for deployment-specific settings:

| Variable | Purpose |
| --- | --- |
| `SQLITE_PATH` | Path to the read-only SQLite file. |
| `LLM_PROVIDER` | Provider name, such as `openai`, `anthropic`, or another compatible API. |
| `LLM_API_KEY` | Server-side LLM API key. |
| `CORS_ORIGINS` | Allowed frontend origins. |
| `LOG_LEVEL` | Runtime logging level. |

Recommended defaults:

- Restrict CORS to the production domain.
- Set API request timeouts for LLM calls.
- Add rate limiting for AI endpoints to control API spend.
- Cache deterministic stats responses with HTTP cache headers.

## Cost Controls

The main recurring risk is not server compute; it is LLM API spend and unindexed database scans.

Controls to implement before public launch:

- Require short prompts and cap response tokens.
- Add per-IP or per-session rate limits for `/api/ai/*`.
- Cache common AI insight responses when based on fixed stats.
- Put a hard timeout on outbound LLM requests.
- Log approximate token usage without logging user secrets.
- Add SQLite indexes for every public filter and sort path.
- Keep SQL agent queries read-only and limit returned rows.
- Add a monthly provider-side LLM spending limit when the provider supports it.

## Observability

Keep monitoring cheap and open-source friendly:

- Use Docker health checks for backend availability.
- Use Caddy access logs with rotation.
- Use `uptime-kuma` on a separate free/cheap host only if needed, or use a free external uptime monitor.
- Start with plain structured logs before adding heavier telemetry.

Minimum health endpoint:

```text
GET /api/health
```

It should verify:

- The app process is running.
- The SQLite file exists and can answer a trivial read-only query.
- It should not call the LLM provider.

## Serverless Alternative

If the project later prioritizes zero server maintenance over preserving FastAPI, use Cloudflare end to end:

```text
Cloudflare Pages
  |-- React frontend
  `-- Pages Functions or Worker API
        |-- Cloudflare D1
        `-- outbound LLM API call
```

This can be the cheapest managed deployment because Cloudflare Pages has a free static hosting tier, Workers Free includes 100,000 requests/day, and D1 Free supports small SQLite-compatible databases. The tradeoff is migration work:

- Rewrite backend endpoints as Worker or Pages Function handlers.
- Import SQLite data into D1 using `wrangler d1 execute --file`.
- Replace Python LangChain SQL agent code with a JavaScript implementation or a simpler SQL-query-generation service.
- Keep the D1 database below the Free plan limits, especially the 500 MB maximum database size.

Use this path only if the dataset is small and the backend stays lightweight.

## Render Free Demo Alternative

For a quick public demo without VM setup:

- Deploy `frontend/` to Cloudflare Pages.
- Deploy `backend/` to Render Free as a Python web service.
- Bundle `youtube.db` with the backend image or repo checkout.
- Set `VITE_API_BASE_URL` to the Render backend URL.

This is easy but not the best production option. Render documents that Free web services spin down after 15 minutes of no inbound traffic, take about a minute to wake, and lose local filesystem changes on redeploy, restart, or spin-down. The SQLite file is safe only if it is bundled as a static artifact and never modified at runtime.

## Deployment Checklist

Before the first public deployment:

- [ ] Add `/api/health`.
- [ ] Add Dockerfile for the backend.
- [ ] Add `docker-compose.yml`.
- [ ] Add `Caddyfile`.
- [ ] Build `data/youtube.db` from a reproducible script.
- [ ] Open SQLite with `mode=ro&immutable=1`.
- [ ] Add CORS allowlist for the production domain.
- [ ] Add API timeouts and rate limits for LLM endpoints.
- [ ] Confirm frontend build works with the production API base URL.
- [ ] Add GitHub Actions for build/test.
- [ ] Document all required environment variables in `README.md`.
