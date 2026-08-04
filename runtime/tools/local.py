from .models import ToolRecord


def local_tools(tools:dict[str,ToolRecord])->tuple[ToolRecord,...]:return tuple(tool for tool in tools.values() if tool.local)
