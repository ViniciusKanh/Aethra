from .chat import router as chat_router
from .health import router as health_router
from .summarize import router as summarize_router
from .vision import router as vision_router

__all__ = ["chat_router", "health_router", "summarize_router", "vision_router"]
