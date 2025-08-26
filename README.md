# Customer Support Agent — FastAPI Microservice (Retrieval-first, Agno-enabled)

---

## Contents
- Quick summary
- Features
- Architecture
- Repository layout
- Quickstart — Docker (recommended)
- Quickstart — local Python (dev only)
- Configuration & environment
- API endpoints & examples
- mTLS / NGINX integration (overview & test)
- Security, audit & compliance notes
- Operational / production checklist
- Troubleshooting
- Contribution & CI suggestions
- Contact

---

## Quick summary
Production-oriented FastAPI microservice for a retrieval-first FAQ customer support agent with semantic search, Agno orchestration, decision-path tracing, JWT RBAC + optional mTLS, audit trail, PII redaction, Prometheus metrics, and Docker deployment.

---

## Features
- Retrieval-first responses using `sentence-transformers` + local cosine similarity.
- Persistent candidate fallback using **ChromaDB**.
- Optional Agno agent orchestration (tool calls, reasoning traces, decision paths).
- Endpoints: `/ask`, `/ingest`, `/tickets`, `/healthz`, `/metrics` (+ dev `/dev/token`).
- JWT authentication and RBAC helper.
- Optional mTLS at the edge (NGINX reverse proxy) with FastAPI header enforcement.
- PII redaction for logs (email, phone, CNIC, CC-like patterns).
- Append-only audit log (`data/audit_log.jsonl`) capturing query, reply and decision metadata.
- Prometheus metrics for observability.
- Dockerized with `Dockerfile` and `docker-compose` (mTLS override example included).
- Developer-friendly: dev token endpoint and sample cert scripts for mTLS testing.

---

## Architecture
1. **Client** → HTTPS → **NGINX** (TLS termination + optional mTLS, forwards `X-SSL-Client-Verify`)  
2. NGINX → internal HTTP → **FastAPI service (agent)**  
3. **FastAPI `/ask`**:
   - compute or reuse embeddings → quick local cosine check
   - if `similarity >= FAQ_CONFIDENCE_THRESHOLD` → return local FAQ
   - else → call Agno agent (if installed) using a small `chroma_tool` to fetch candidates; agent output and tool call trace → returned as `decision`
4. **Audit & metrics**: redact PII → write audit JSONL entry → increment Prometheus metrics
5. **Escalation**: `/tickets` writes a ticket and audit entry (CSV + JSONL)

---

## Repository layout
```
project-root/
├─ docker/                      # Docker artifacts, nginx config, cert scripts
│  ├─ Dockerfile
│  ├─ docker-compose.yml
│  ├─ nginx/
│  │  ├─ nginx.conf
│  │  └─ gen_cert.sh
├─ src/
│  ├─ app.py                     # FastAPI app and endpoints
│  ├─ ingest.py                  # ingestion wrapper
│  ├─ ingest_faq.py              # original ingest script
│  ├─ agno_agent.py              # Agno wrapper + decision path
│  ├─ customer_support_agent.py  # local retrieval logic
│  ├─ mtls.py                    # FastAPI mTLS enforcement dependency
│  ├─ security.py                # JWT helpers and RBAC
│  ├─ pii_redact.py              # simple PII redaction
│  └─ audit.py                   # append-only audit writer
├─ data/
│  ├─ faq.csv
│  └─ tickets.csv
├─ requirements.txt
├─ README.md
```

---

## Quickstart — Docker (recommended)
> Assumes `docker` and `docker-compose` are installed and Docker Desktop is running.

1. **Generate dev certs for mTLS (optional)**  
   ```bash
   bash docker/nginx/gen_cert.sh
   ```
   This creates `docker/nginx/certs/{ca.crt,server.crt,server.key,client.crt,client.key}`.

2. **Start the services**  
   ```bash
   cd docker
   docker-compose up --build -d
   ```

3. **Get a dev JWT** (dev-only helper)
   - If nginx mTLS is not enabled: `http://localhost:8000/dev/token`
   - If nginx mTLS enabled and listening at `https://localhost:8443`: call via client certs (curl example below).

4. **Test /ask** (with mTLS + JWT if enabled) — see API examples below.

---

## Quickstart — local Python (dev only)
1. Create venv and install:
   ```bash
   python -m venv .venv
   # mac/linux
   source .venv/bin/activate
   # windows PowerShell
   .\.venv\Scripts\Activate.ps1

   pip install -r requirements.txt
   ```

2. Populate `data/faq.csv` (header: `id,question,answer,category`).

3. Start FastAPI:
   ```bash
   uvicorn src.app:app --reload --port 8000
   ```

> Use this for rapid development. Docker is recommended for parity with deployment.

---

## Configuration & environment
Create a `.env` (or set env vars) with these keys:
```
FAQ_CSV=/app/data/faq.csv
CHROMA_PATH=/app/chroma_db
FAQ_COLLECTION_NAME=faq_collection
LOCAL_EMB_MODEL=all-MiniLM-L6-v2
FAQ_CONFIDENCE_THRESHOLD=0.7
JWT_SECRET=change-me
AUDIT_FILE=/app/data/audit_log.jsonl
ENFORCE_MTLS=true   # set true when running behind nginx mTLS
```

---

## API endpoints & examples

> All protected endpoints require `Authorization: Bearer <jwt>` (except `/healthz`, and `/dev/token` for dev).

### GET `/healthz`
Returns:
```json
{ "status": "ok" }
```

### POST `/dev/token` (dev only)
Form data: `username`, `role` → returns `{ "token": "<jwt>" }`

### POST `/ingest` (protected)
Triggers ingestion of `data/faq.csv` into Chroma:
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Authorization: Bearer <TOKEN>"
```

### POST `/ask` (protected)
Body:
```json
{ "user_id": "u1", "message": "How do I reset my password?" }
```
Example curl (no mTLS):
```bash
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","message":"How do I reset my password?"}'
```
Example curl (with nginx mTLS on 8443):
```bash
curl --cacert docker/nginx/certs/ca.crt \
     --cert docker/nginx/certs/client.crt --key docker/nginx/certs/client.key \
     -X POST https://localhost:8443/ask \
     -H "Authorization: Bearer <TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"user_id":"u1","message":"refund policy?"}'
```

### POST `/tickets` (protected)
Body:
```json
{ "user_id":"u1", "message":"Please escalate billing issue." }
```
Appends to `data/tickets.csv` and audit log.

### GET `/metrics`
Prometheus metrics (text/plain).

---

## mTLS / NGINX integration — Overview & test
- NGINX terminates TLS and enforces client certificates (mTLS). It forwards the verification result in `X-SSL-Client-Verify` which FastAPI checks via `src/mtls.py` when `ENFORCE_MTLS=true`.
- For local testing:
  1. Run `bash docker/nginx/gen_cert.sh` to create CA, server, and client certs.
  2. Run Docker Compose with nginx mounted (see Docker Compose in repo).
  3. Use curl or Postman with the generated client certs: `--cert client.crt --key client.key --cacert ca.crt`.

---

## Security, audit & compliance notes
- **Authentication:** Replace the dev `/dev/token` with an enterprise OIDC/JWKS provider for production.
- **Authorization:** Use `security.require_role()` helper for RBAC checks; map roles to SSO groups.
- **mTLS:** Enforce at ingress (NGINX/Envoy). FastAPI performs header-check as defence-in-depth.
- **PII:** Regex-based redaction implemented; for regulated environments use a dedicated PII detection pipeline.
- **Audit:** All interactions are appended to `data/audit_log.jsonl`. For production, stream audits to an immutable, access-controlled store.
- **Secrets:** Use a secret manager (Vault, AWS Secrets Manager)—do not commit secrets to the repo.

---

## Operational / production checklist
- Use CPU-only embeddings in production unless GPUs required: pin CPU wheels or host embeddings separately.
- Replace `/dev/token` with company SSO and validate JWT via JWKS.
- Store audit logs in encrypted, append-only storage.
- Add structured JSON logging and traces (OpenTelemetry).
- Implement CI to lint, test, run `pip-audit`, and build signed images.
- Harden the reverse-proxy and TLS config (HSTS, OCSP, cipher restrictions).
- Backup and rotate Chroma DB and audit logs.

---

## Troubleshooting
- **Large Docker images**: `sentence-transformers` → `transformers` → `torch` pulls large wheels. For dev, remove heavy libs or pin CPU-only torch.
- **Docker disk usage**: move Docker's disk image to another drive or prune unused images: `docker system prune -a --volumes`.
- **mTLS errors**: verify CA, client cert, and use `--cacert` with curl or import CA into system trust store.
- **Chroma errors**: ensure `CHROMA_PATH` is writable and ingestion succeeded.

---

## Contribution & CI suggestions
- Fork → feature branch → PR. Keep PRs small.
- Add unit tests for core utilities: PII redaction, cosine similarity, ingestion.
- CI pipeline: lint, type-check, security scan, unit tests, build image, push to registry.
- Produce a `requirements-lock.txt` from CI for reproducible deployments.

---
## Contact

**Syed Burhan** — Project owner & maintainer.

- LinkedIn: https://www.linkedin.com/in/syed-burhan-2a73b7272/
- Email: burhansyed579@gmail.com
- Blog: https://medium.com/@hafizburhan0684

For bugs or feature requests, please use GitHub Issues.

