from ..models import EnterpriseChatRequest, EnterpriseChatResponse, UserResponse
from .conversation_service import ConversationService
from .knowledge_service import KnowledgeService


class AssistantService:
    """Chat documental com historico persistente e isolado por usuario."""

    def __init__(self, knowledge_service: KnowledgeService, conversation_service: ConversationService) -> None:
        self.knowledge = knowledge_service
        self.conversations = conversation_service

    def execute(self, payload: EnterpriseChatRequest, user: UserResponse) -> EnterpriseChatResponse:
        if payload.conversation_id:
            conversation_id = payload.conversation_id
            history = self.conversations.history(user.id, conversation_id, limit=10)
        else:
            conversation = self.conversations.create(user.id, payload.pergunta)
            conversation_id = conversation.id
            history = payload.historico[-10:]

        grounded_payload = payload.model_copy(update={"historico": history, "conversation_id": conversation_id})
        result = self.knowledge.ask(grounded_payload, conversation_id)
        self.conversations.add_exchange(
            user.id,
            conversation_id,
            payload.pergunta,
            result.resposta,
            result.citations,
        )
        return result
