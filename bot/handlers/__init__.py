# bot/handlers root barrel: re-exports domain routers for backwards compatibility
from .campaigns import campaign_router, template_router
from .leads import target_router, blacklist_router, pain_point_router
from .accounts import account_router
from .conversations import replies_router, war_room_router, approval_router
from .reporting import stats_router, export_router, dashboard_router

# Backwards compatibility aliases
target_handler = target_router
replies_handler = replies_router
pain_point_handler = pain_point_router
export_handler = export_router
stats_handler = stats_router
blacklist_handler = blacklist_router
war_room_handler = war_room_router

__all__ = [
    "campaign_router", "template_router",
    "target_router", "blacklist_router", "pain_point_router",
    "account_router",
    "replies_router", "war_room_router", "approval_router",
    "stats_router", "export_router", "dashboard_router"
]
