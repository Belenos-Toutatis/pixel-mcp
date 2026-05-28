"""FastMCP entrypoint — Google Health API (Pixel Watch & co.)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .client import HealthClient
from .tools import (
    register_users,
    register_devices,
    register_datapoints,
    register_convenience,
    register_writes,
)

mcp = FastMCP("pixel-mcp")
_client = HealthClient()

register_users(mcp, _client)
register_devices(mcp, _client)
register_datapoints(mcp, _client)
register_convenience(mcp, _client)
register_writes(mcp, _client)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
