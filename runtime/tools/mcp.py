from .models import MCPServerRecord


def available_mcp_servers(servers:dict[str,MCPServerRecord])->tuple[MCPServerRecord,...]:return tuple(servers.values())
