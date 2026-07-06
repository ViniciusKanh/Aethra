from .admin import router as admin_router
from .auth import router as auth_router
from .chat import router as chat_router
from .conversations import router as conversations_router
from .health import router as health_router
from .knowledge import router as knowledge_router
from .summarize import router as summarize_router
from .vision import router as vision_router

__all__ = [name for name in globals() if name.endswith("_router")]
