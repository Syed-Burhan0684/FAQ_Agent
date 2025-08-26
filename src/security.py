import os
import jwt
import time
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()
JWT_SECRET = os.getenv('JWT_SECRET', 'changeme')
JWT_ALG = 'HS256'

security = HTTPBearer()

def create_jwt_token(payload: dict, exp_seconds: int = 3600):
    p = payload.copy()
    p['exp'] = int(time.time()) + exp_seconds
    return jwt.encode(p, JWT_SECRET, algorithm=JWT_ALG)


# require_jwt dependency for protected endpoints
def require_jwt(creds: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token = creds.credentials
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token'
        )
    # simple RBAC check example: 'roles' claim must include 'user' or 'admin'
    roles = data.get('roles', [])
    if not roles:
        raise HTTPException(status_code=403, detail='No roles in token')
    return data


# helper to check role inside an endpoint
def require_role(role: str):
    def _checker(payload: dict = Depends(require_jwt)):
        if role not in payload.get('roles', []):
            raise HTTPException(status_code=403, detail='Insufficient role')
        return payload
    return _checker
