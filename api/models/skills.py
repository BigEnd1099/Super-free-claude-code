from pydantic import BaseModel
from typing import List, Optional

class SkillInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    path: str
    version: Optional[str] = None

class SkillListResponse(BaseModel):
    data: List[SkillInfo]
