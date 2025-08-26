# src/agno_adapter.py
from typing import Dict, Any
import os, time

# Try import agno
try:
    from agno.agent import Agent
    from agno.tools import Tool
    AGNO_AVAILABLE = True
except Exception:
    AGNO_AVAILABLE = False

# Reuse local retrieval code from your existing files
# We'll import your customer_agent_agno functions if available
try:
    from customer_agent_agno import find_best_local_match, query_chroma_candidates, format_chroma_results
except Exception:
    # fallback naive
    def find_best_local_match(q):
        return 0.0, {}
    def query_chroma_candidates(q, k=5):
        return {"documents": [[]], "metadatas": [[]], "ids": [[]], "distances": [[]]}
    def format_chroma_results(res):
        return "No candidates available"

def run_agno_for_query(query: str, user_id: str = "anon") -> Dict[str, Any]:
    # 1) local best match
    best_sim, best_faq = find_best_local_match(query)
    decision_path = []
    decision_path.append({"step": "local_similarity", "score": float(best_sim), "candidate": best_faq})
    # If confident, return the FAQ answer
    threshold = float(os.getenv("FAQ_CONFIDENCE_THRESHOLD", "0.70"))
    if best_sim >= threshold and best_faq:
        return {"reply": best_faq.get("answer", ""), "confidence": float(best_sim), "decision_path": decision_path}
    # Otherwise use chroma fallback
    chroma_res = query_chroma_candidates(query, k=5)
    formatted = format_chroma_results(chroma_res)
    decision_path.append({"step": "chroma_candidates", "candidates_summary": formatted})
    # If Agno available, we could call agent.run() here to orchestrate; for now return candidates text
    # Build a reply summarizing top candidate
    docs = chroma_res.get("documents", [[]])[0]
    reply = docs[0] if docs and docs[0] else "I couldn't find a confident FAQ match. A ticket can be raised for human support."
    # confidence heuristic: use distance or fallback to 0.4
    try:
        conf = float(chroma_res.get("distances", [[]])[0][0])
        # if chroma returns distance a smaller value means closer in some versions; keep it safe:
        conf = max(0.0, min(1.0, 1.0 - conf)) if conf is not None else 0.4
    except Exception:
        conf = 0.4
    return {"reply": reply, "confidence": conf, "decision_path": decision_path}
