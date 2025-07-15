from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Memory:
    id: Optional[str] = None
    type: str = "note"  # e.g., note, fact, event
    content: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "Memory":
        return Memory(
            id=data.get("id"),
            type=data.get("type", "note"),
            content=data.get("content", ""),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else datetime.utcnow(),
            tags=data.get("tags", [])
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags
        }
