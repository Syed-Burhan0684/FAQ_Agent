# test_import_agno.py
try:
    import agno
    print("AGNO import OK, version:", getattr(agno, "__version__", "unknown"))
    from agno.agent import Agent
    from agno.tools import Tool
    print("Agent and Tool import OK")
except Exception as e:
    print("IMPORT ERROR:", repr(e))
