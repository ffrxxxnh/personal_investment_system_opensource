# Integrations Blueprint
# src/web_app/blueprints/integrations/__init__.py

"""
Data integrations management blueprint.

Provides web routes for:
- Data source dashboard
- Connector configuration
- Sync management
- Import history
"""

from flask import Blueprint

integrations_bp = Blueprint(
    'integrations',
    __name__,
    url_prefix='/integrations',
    template_folder='templates'
)

from . import routes  # noqa: E402, F401
