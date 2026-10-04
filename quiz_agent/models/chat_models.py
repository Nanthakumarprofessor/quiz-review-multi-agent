# chat_models.py
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequestDTO(BaseModel):
    user_id: int
    query: str
    difficulty: str
    questions_count: int
    answers: Optional[List[str]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "query": "Python programming",
                "difficulty": "medium",
                "questions_count": 3,
                "answers": ["Guido van Rossum", "Indentation", "Dynamically typed"]
            }
        }


class AgentResponse(BaseModel):
    user_id: int = Field(description="The user ID this response belongs to")
    response: str = Field(description="The final review/evaluation response")