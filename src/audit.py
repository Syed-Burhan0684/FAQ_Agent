# File: src/audit.py
# -------------------------
import os
import json
import time

AUDIT_FILE = os.getenv('AUDIT_FILE', 'data/audit_log.jsonl')

# Ensure directory exists
os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)


def record_audit(user_id: str, query: str, reply: str, decision: dict, confident: bool, similarity: float):
    entry = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': user_id,
        'query': query,
        'reply': reply,
        'decision': decision,
        'confident': bool(confident),
        'similarity': float(similarity)
    }
    with open(AUDIT_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')
# -------------------------
