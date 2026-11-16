# Domain barrel: campaigns handlers
from .campaign_handler import router as campaign_router
from .template_handler import router as template_router

__all__ = ["campaign_router", "template_router"]
