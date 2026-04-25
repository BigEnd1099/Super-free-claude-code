from pydantic import BaseModel


class SkillInfo(BaseModel):
    id: str
    name: str
    description: str | None = None
    path: str
    version: str | None = None
    category: str | None = None
    tags: list[str] = []


class SkillListResponse(BaseModel):
    data: list[SkillInfo]
