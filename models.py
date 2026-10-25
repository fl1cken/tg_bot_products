from pydantic import BaseModel
from typing import List, Optional

class User(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None

class Item(BaseModel):
    id: int
    name: str
    price: float
    owners: List[int] = []

class Check(BaseModel):
    id: int
    buyer_id: int
    items: List[Item] = []
    status: str = 'active'

class CheckCreate(BaseModel):
    buyer_id: int
    items: List[dict]