from .auth import router as auth_router
from .devices import router as devices_router
from .assessments import router as assessments_router
from .recommendations import router as recommendations_router
from .providers import router as providers_router
from .recovery import router as recovery_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "devices_router",
    "assessments_router",
    "recommendations_router",
    "providers_router",
    "recovery_router",
    "admin_router",
]
