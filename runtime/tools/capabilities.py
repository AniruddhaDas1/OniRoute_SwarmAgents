from enum import StrEnum


class ToolCapability(StrEnum):
    FILESYSTEM="filesystem"; TERMINAL="terminal"; BROWSER="browser"; DATABASE="database"; SEARCH="search"; EMAIL="email"; CALENDAR="calendar"; GITHUB="github"; GIT="git"; DOCKER="docker"; KUBERNETES="kubernetes"; SUPABASE="supabase"; APPWRITE="appwrite"; POSTGRES="postgres"; REDIS="redis"; HTTP="http"; MCP="mcp"; IMAGE="image"; VISION="vision"; AUDIO="audio"; DOCUMENTS="documents"; SPREADSHEETS="spreadsheets"; PRESENTATIONS="presentations"; REASONING="reasoning"; CODE_EXECUTION="code_execution"
