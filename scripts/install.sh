#!/usr/bin/env bash
# cross-platform installer for OniRoute

set -e

# Colored output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing OniRoute...${NC}"

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${OS}"
esac

echo -e "${GREEN}Detected OS: ${machine}${NC}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python >= 3.12.${NC}"
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ $(echo "$PY_VER < 3.12" | bc -l) -eq 1 ]]; then
    echo -e "${RED}Python version ${PY_VER} is not supported. Please install Python >= 3.12.${NC}"
    exit 1
fi
echo -e "${GREEN}Python version ${PY_VER} is supported.${NC}"

# Check Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Git is not installed. Please install Git.${NC}"
    exit 1
fi
echo -e "${GREEN}Git is installed.${NC}"

# Options
echo "Choose installation method:"
echo "1) pip (virtual environment recommended)"
echo "2) pipx (isolated global installation)"
echo "3) from source"
read -p "Select [1-3]: " choice

case $choice in
    1)
        echo -e "${YELLOW}Installing via pip...${NC}"
        pip install oniroute-swarmagents
        ;;
    2)
        echo -e "${YELLOW}Installing via pipx...${NC}"
        if ! command -v pipx &> /dev/null; then
            echo -e "${RED}pipx is not installed. Please install pipx first.${NC}"
            exit 1
        fi
        pipx install oniroute-swarmagents
        ;;
    3)
        echo -e "${YELLOW}Installing from source...${NC}"
        git clone https://github.com/AniruddhaDas1/OniRoute_SwarmAgents.git /tmp/OniRoute_SwarmAgents
        cd /tmp/OniRoute_SwarmAgents
        pip install -e .
        ;;
    *)
        echo -e "${RED}Invalid choice.${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}OniRoute successfully installed!${NC}"
echo "Run 'oniroute init' to get started."
