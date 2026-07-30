#!/usr/bin/env bash
# Vibe2Fig installer — idempotent. Run from anywhere:
#   curl -fsSL https://raw.githubusercontent.com/CodyChuGit/Vibe2Fig/main/install.sh | bash
# or from a clone: ./install.sh
set -euo pipefail

REPO_URL="https://github.com/CodyChuGit/Vibe2Fig.git"
DEFAULT_DIR="$HOME/Vibe2Fig"

say() { printf '\033[1;33m[vibe2fig]\033[0m %s\n' "$*"; }

# 1. Locate or clone the repo
if [ -f "$(dirname "$0")/vibe2fig_skill/SKILL.md" ] 2>/dev/null; then
  DIR="$(cd "$(dirname "$0")" && pwd)"
  say "using existing checkout: $DIR"
else
  DIR="$DEFAULT_DIR"
  if [ -d "$DIR/.git" ]; then
    say "updating $DIR"
    git -C "$DIR" pull --ff-only
  else
    say "cloning to $DIR"
    git clone "$REPO_URL" "$DIR"
  fi
fi

# 2. Python dependency (Pillow — capture/measure/asset tools)
if ! python3 -c 'import PIL' 2>/dev/null; then
  say "installing Pillow"
  python3 -m pip install --user pillow || pip3 install pillow
else
  say "Pillow ok"
fi

# 3. Figma MCP server — auto-register when a supported agent CLI is present
if command -v claude >/dev/null 2>&1; then
  if claude mcp list 2>/dev/null | grep -qi figma; then
    say "Figma MCP already configured"
  else
    say "registering Figma MCP server with detected agent CLI"
    claude mcp add --transport http figma https://mcp.figma.com/mcp || \
      say "WARN: auto-registration failed — add https://mcp.figma.com/mcp to your agent's MCP config"
  fi
else
  say "NOTE: no agent CLI detected — register https://mcp.figma.com/mcp in your agent's MCP config"
fi

# 4. Install the skill (symlink tracks the repo)
# SKILL_DIR: your agent's skills directory; override for other agents, e.g.
#   SKILL_DIR=~/.myagent/skills ./install.sh
SKILL_DIR="${SKILL_DIR:-$HOME/.claude/skills}"
mkdir -p "$SKILL_DIR"
if [ ! -e "$SKILL_DIR/vibe2fig" ]; then
  ln -s "$DIR/vibe2fig_skill" "$SKILL_DIR/vibe2fig"
  say "skill installed -> $SKILL_DIR/vibe2fig"
else
  say "skill already installed at $SKILL_DIR/vibe2fig"
fi

say "done. Ask your agent: \"turn this app into a Figma file\""
say "optional: install the UI/UX Pro Max skill for layout quality (recommended)"
