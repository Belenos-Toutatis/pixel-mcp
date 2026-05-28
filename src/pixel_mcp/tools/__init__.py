"""MCP tools for the Google Health API (Pixel Watch & co.)."""

from .users import register as register_users
from .devices import register as register_devices
from .datapoints import register as register_datapoints
from .convenience import register as register_convenience
from .writes import register as register_writes

__all__ = [
    "register_users",
    "register_devices",
    "register_datapoints",
    "register_convenience",
    "register_writes",
]
