# src/app.py
from fastapi import FastAPI, Depends
from fastapi.responses import Response
import time
import os

# auth / security
from .security import require_jwt, create_jwt_token

# app utilities
from prometheus_client import generate_latest
from .audit import record_audit
from .pii_redact import redact_pii
from .ingest_faq import ingest_faq_from_csv
from .agno_agent import ask_with_agno

# models & metrics
from .models import AskReq, AskResp, IngestResp, TicketReq, TicketResp, DevTokenRequest
from .metrics import REQUEST_COUNT, REQUEST_LATENCY

app = FastAPI(title="Customer Support Agent (service)")

# health check endpoint
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# metrics endpoint for Prometheus to scrape
@app.get("/metrics")
def metrics():
    # generate_latest() returns bytes; return as plain text response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4")

# ingest endpoint (protected)
@app.post("/ingest", response_model=IngestResp)
def ingest(_auth: dict = Depends(require_jwt)):
    start = time.time()
    ingested = ingest_faq_from_csv()
    REQUEST_COUNT.labels(endpoint="/ingest", method="POST", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/ingest").observe(time.time() - start)
    return IngestResp(ingested=ingested)

# ask endpoint
@app.post("/ask", response_model=AskResp)
def ask(req: AskReq, _auth: dict = Depends(require_jwt)):
    start = time.time()
    safe_msg = redact_pii(req.message)
    reply, confident, similarity, decision = ask_with_agno(req.user_id, safe_msg)
    record_audit(
        user_id=req.user_id,
        query=safe_msg,
        reply=reply,
        decision=decision,
        confident=confident,
        similarity=similarity,
    )
    REQUEST_COUNT.labels(endpoint="/ask", method="POST", status="200").inc()
    REQUEST_LATENCY.labels(endpoint="/ask").observe(time.time() - start)
    return AskResp(reply=reply, confident=confident, similarity=similarity, decision=decision)

# tickets endpoint for escalation
@app.post("/tickets", response_model=TicketResp)
def create_ticket_endpoint(req: TicketReq, _auth: dict = Depends(require_jwt)):
    tid = str(int(time.time() * 1000))
    os.makedirs("data", exist_ok=True)
    with open("data/tickets.csv", "a", encoding="utf-8") as f:
        f.write(f"{tid},{time.strftime('%Y-%m-%d %H:%M:%S')},{req.user_id},{req.message},open\n")
    record_audit(
        user_id=req.user_id,
        query=req.message,
        reply="[escalated]",
        decision={"escalated": True},
        confident=False,
        similarity=0.0,
    )
    REQUEST_COUNT.labels(endpoint="/tickets", method="POST", status="200").inc()
    return TicketResp(ticket_id=tid)

# dev helper: mint JWT (dev-only)
@app.post("/dev/token")
def dev_token(req: DevTokenRequest):
    token = create_jwt_token({"sub": req.username, "roles": [req.role]})
    return {"token": token}
