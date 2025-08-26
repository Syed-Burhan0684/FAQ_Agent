# src/auth.py
# backward-compat shim: re-export functions from security.py
from .security import create_jwt_token, require_jwt, require_role

__all__ = ["create_jwt_token", "require_jwt", "require_role"]
