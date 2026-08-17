"""
Routes
------
The routed layer — one folder per resource, each owning a Blueprint.

BLUEPRINTS is the single list create_app() registers. Adding a resource means
adding a folder and one line here; nothing else in the application changes.
"""

from adrag.routes.query.query_routes import query_bp
from adrag.routes.knowledge_base.knowledge_base_routes import knowledge_base_bp
from adrag.routes.provider.provider_routes import provider_bp
from adrag.routes.health_check.health_check_routes import health_check_bp

BLUEPRINTS = (
    query_bp,
    knowledge_base_bp,
    provider_bp,
    health_check_bp,
)
