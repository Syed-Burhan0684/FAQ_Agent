# src/agno_agent.py
"""Wrapper around Agno agent to perform retrieval-first behavior and return decision path.
This file uses Agno when available; otherwise falls back to cosine-similarity local logic.
"""
import os
import traceback
from typing import Tuple, Dict, Any

# try to import agno (robust to different Agno versions)
AGNO_AVAILABLE = False
Agent = None
TOOL_WRAPPER = None

try:
    import agno
    # dynamic import of Agent to avoid hard ImportError on older/newer versions
    Agent = getattr(__import__('agno.agent', fromlist=['Agent']), 'Agent')
    # try multiple possible tool entrypoints (Tool class or tool decorator)
    try:
        TOOL_WRAPPER = getattr(__import__('agno.tools', fromlist=['Tool']), 'Tool')
    except Exception:
        try:
            TOOL_WRAPPER = getattr(__import__('agno.tools', fromlist=['tool']), 'tool')
        except Exception:
            # fallback: identity decorator so functions remain callables
            TOOL_WRAPPER = lambda f: f
    AGNO_AVAILABLE = True
    print(f"DEBUG: agno imported successfully, version={getattr(agno, '__version__', 'unknown')}, TOOL_WRAPPER={TOOL_WRAPPER}")
except Exception as e:
    AGNO_AVAILABLE = False
    print("DEBUG: Failed to import agno in agno_agent.py:", repr(e))

# import local similarity helpers from user's original code if present
try:
    # try relative import first (package usage)
    from .customer_agent import find_best_local_match, query_chroma_candidates
except Exception as e1:
    try:
        # fallback to top-level import if running as script
        from customer_agent import find_best_local_match, query_chroma_candidates
    except Exception as e2:
        print("Failed to import customer_agent:", repr(e1), repr(e2))
        # fallback simple stubs (but we log the failure)
        def find_best_local_match(q):
            # return similarity, faq dict
            return 0.0, {}
        def query_chroma_candidates(q, k=5):
            return {'documents': [[]], 'metadatas': [[]], 'ids': [[]], 'distances': [[]]}


def _format_chroma_result_for_reply(res):
    docs = res.get('documents', [[]])[0] if isinstance(res.get('documents'), list) else res.get('documents', [])
    metas = res.get('metadatas', [[]])[0] if isinstance(res.get('metadatas'), list) else res.get('metadatas', [])
    if docs and docs[0]:
        first_doc = docs[0]
        first_meta = metas[0] if metas and isinstance(metas[0], dict) else {}
        q = first_meta.get('question', '')
        a = first_doc
        return f"Q: {q}\nA: {a}"
    else:
        return "No match found"


# main API used by app.ask
def ask_with_agno(user_id: str, message: str) -> Tuple[str, bool, float, Dict[str, Any]]:
    """Return (reply, confident, similarity, decision)"""
    # 1) try local best-match (fast)
    best_sim, best_faq = find_best_local_match(message)
    decision = {'local_best_sim': float(best_sim)}
    CONF_THRESH = float(os.getenv('FAQ_CONFIDENCE_THRESHOLD', '0.7'))
    if best_sim >= CONF_THRESH and best_faq:
        decision['path'] = 'local_best'
        decision['faq_id'] = best_faq.get('id')
        return best_faq.get('answer', ''), True, float(best_sim), decision

    # 2) if Agno available, call agent with a tool that returns chroma candidates
    if AGNO_AVAILABLE:
        try:
            @TOOL_WRAPPER
            def chroma_tool(query: str) -> str:
                res = query_chroma_candidates(query, k=5)
                # format results compactly
                docs = res.get('documents', [[]])[0] if isinstance(res.get('documents'), list) else res.get('documents', [])
                metas = res.get('metadatas', [[]])[0] if isinstance(res.get('metadatas'), list) else res.get('metadatas', [])
                out_lines = []
                for i, d in enumerate(docs):
                    qmeta = metas[i].get('question', '') if i < len(metas) and isinstance(metas[i], dict) else ''
                    out_lines.append(f"FAQ#{i} Q:{qmeta} A:{d}")
                return '\n'.join(out_lines)

            # Create the agent. Be tolerant to Agent signature differences.
            try:
                agent = Agent(
                    name='support-agent',
                    role='Answer user questions using FAQ data; call chroma_tool for candidates; if unsure, escalate.',
                    tools=[chroma_tool],
                    instructions=["Prefer direct FAQ answers. If uncertain, return top candidates and suggest escalation."],
                )
            except TypeError:
                # some Agno versions may require different parameter names; try with fallback args
                try:
                    agent = Agent('support-agent', 'Answer user questions using FAQ data', tools=[chroma_tool])
                except Exception as e:
                    print("DEBUG: Agent construction failed:", repr(e))
                    decision['agent_error'] = str(e)
                    agent = None

            if agent is not None:
                # run agent synchronously if API allows; otherwise try arun
                try:
                    resp = agent.run(message)
                    decision['path'] = 'agno_agent'
                    # try to extract textual content from possible response structures
                    if hasattr(resp, "content"):
                        reply = resp.content
                    elif isinstance(resp, dict) and 'content' in resp:
                        reply = resp['content']
                    else:
                        reply = str(resp)
                    decision['agno_output'] = reply
                    return reply, False, float(best_sim), decision
                except Exception as run_e:
                    # log full traceback for debugging and try async
                    tb = traceback.format_exc()
                    print("DEBUG: Agno agent.run error:", tb)
                    decision['agno_error'] = str(run_e)
                    decision['agno_trace'] = tb
                    try:
                        import asyncio
                        resp = asyncio.run(agent.arun(message))
                        decision['path'] = 'agno_agent_async'
                        if hasattr(resp, "content"):
                            reply = resp.content
                        elif isinstance(resp, dict) and 'content' in resp:
                            reply = resp['content']
                        else:
                            reply = str(resp)
                        decision['agno_output'] = reply
                        return reply, False, float(best_sim), decision
                    except Exception as arun_e:
                        tb2 = traceback.format_exc()
                        print("DEBUG: Agno agent.arun error:", tb2)
                        decision['agno_error_async'] = str(arun_e)
                        decision['agno_trace_async'] = tb2
        except Exception as e:
            decision['tool_error'] = str(e)

    # 3) fallback: return chroma candidates formatted simply
    res = query_chroma_candidates(message, k=5)
    reply = _format_chroma_result_for_reply(res)
    decision['path'] = 'chroma_fallback'
    return reply, False, float(best_sim), decision
