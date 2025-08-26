# src/models.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class AskReq(BaseModel):
    user_id: Optional[str] = "anon"
    message: str

class AskResp(BaseModel):
    reply: str
    confident: bool
    similarity: float
    decision: Dict[str, Any] = {}

class IngestResp(BaseModel):
    ingested: int

class TicketReq(BaseModel):
    user_id: Optional[str] = "anon"
    message: str

class TicketResp(BaseModel):
    ticket_id: str

class DevTokenRequest(BaseModel):
    username: str
    role: str = "user"
