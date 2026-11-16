# Domain barrel: leads handlers
from .target_handler import router as target_router
from .blacklist_handler import router as blacklist_router
from .pain_point_handler import router as pain_point_router

__all__ = ["target_router", "blacklist_router", "pain_point_router"]
