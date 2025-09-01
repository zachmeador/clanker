"""Example app package."""

from clanker.exports import register_app_exports

# Import exports module to trigger decorator registration
from . import exports

# Register exports with Clanker
register_app_exports("example", exports)
