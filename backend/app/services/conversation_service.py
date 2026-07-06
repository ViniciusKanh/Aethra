import json
from datetime import UTC, datetime
from uuid import uuid4

from ..models import (
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
    KnowledgeCitation,
    StoredMessage,
)
from .turso_service import TursoService
from .user_service import AuthError


class ConversationService:
    """Historico pessoal de chat persistido no Turso."""

    def __init__(self, turso_service: TursoService) -> None:
        self.turso = turso_service

    def create(self, user_id: str, first_question: str) -> ConversationSummary:
        now = self._now()
        conversation_id = str(uuid4())
        title = " ".join(first_question.strip().split())[:72] or "Nova conversa"
        self.turso.execute(
            "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            [conversation_id, user_id, title, now, now],
        )
        return ConversationSummary(
            id=conversation_id,
            title=title,
            created_at=now,
            updated_at=now,
            message_count=0,
        )

    def list_conversations(self, user_id: str) -> list[ConversationSummary]:
        rows = self.turso.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at, COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE c.user_id = ?
            GROUP BY c.id, c.title, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
            LIMIT 100
            """,
            [user_id],
        ).rows
        return [ConversationSummary(**row) for row in rows]

    def get(self, user_id: str, conversation_id: str) -> ConversationDetail:
        conversation = self._owned_conversation(user_id, conversation_id)
        rows = self.turso.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at, id",
            [conversation_id],
        ).rows
        messages: list[StoredMessage] = []
        for row in rows:
            try:
                raw_citations = json.loads(str(row.get("citations_json") or "[]"))
            except json.JSONDecodeError:
                raw_citations = []
            citations = [KnowledgeCitation(**item) for item in raw_citations if isinstance(item, dict)]
            messages.append(
                StoredMessage(
                    id=str(row["id"]),
                    role=str(row["role"]),
                    content=str(row["content"]),
                    citations=citations,
                    created_at=str(row["created_at"]),
                )
            )
        return ConversationDetail(
            id=str(conversation["id"]),
            title=str(conversation["title"]),
            created_at=str(conversation["created_at"]),
            updated_at=str(conversation["updated_at"]),
            message_count=len(messages),
            messages=messages,
        )

    def history(self, user_id: str, conversation_id: str, limit: int = 10) -> list[ConversationMessage]:
        self._owned_conversation(user_id, conversation_id)
        rows = self.turso.execute(
            """
            SELECT role, content FROM (
                SELECT id, role, content, created_at FROM messages
                WHERE conversation_id = ? ORDER BY created_at DESC, id DESC LIMIT ?
            ) recent ORDER BY created_at, id
            """,
            [conversation_id, limit],
        ).rows
        return [ConversationMessage(role=str(row["role"]), content=str(row["content"])) for row in rows]

    def add_exchange(
        self,
        user_id: str,
        conversation_id: str,
        question: str,
        answer: str,
        citations: list[KnowledgeCitation],
    ) -> None:
        self._owned_conversation(user_id, conversation_id)
        now = self._now()
        self.turso.transaction([
            (
                "INSERT INTO messages (id,conversation_id,role,content,citations_json,created_at) VALUES (?,?,'user',?,'[]',?)",
                [str(uuid4()), conversation_id, question, now],
            ),
            (
                "INSERT INTO messages (id,conversation_id,role,content,citations_json,created_at) VALUES (?,?,'assistant',?,?,?)",
                [
                    str(uuid4()),
                    conversation_id,
                    answer,
                    json.dumps([item.model_dump() for item in citations], ensure_ascii=False),
                    self._now(),
                ],
            ),
            ("UPDATE conversations SET updated_at = ? WHERE id = ?", [self._now(), conversation_id]),
        ])

    def delete(self, user_id: str, conversation_id: str) -> None:
        self._owned_conversation(user_id, conversation_id)
        self.turso.transaction([
            ("DELETE FROM messages WHERE conversation_id = ?", [conversation_id]),
            ("DELETE FROM conversations WHERE id = ? AND user_id = ?", [conversation_id, user_id]),
        ])

    def _owned_conversation(self, user_id: str, conversation_id: str) -> dict[str, object]:
        rows = self.turso.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ? LIMIT 1",
            [conversation_id, user_id],
        ).rows
        if not rows:
            raise AuthError(404, "Conversa nao encontrada.")
        return rows[0]

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
