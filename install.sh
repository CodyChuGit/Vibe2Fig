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

# 3. Figma MCP server (needs the claude CLI)
if command -v claude >/dev/null 2>&1; then
  if claude mcp list 2>/dev/null | grep -qi figma; then
    say "Figma MCP already configured"
  else
    say "adding Figma MCP server"
    claude mcp add --transport http figma https://mcp.figma.com/mcp || \
      say "WARN: could not add Figma MCP automatically — run: claude mcp add --transport http figma https://mcp.figma.com/mcp"
  fi
else
  say "WARN: claude CLI not found — install Claude Code, then run: claude mcp add --transport http figma https://mcp.figma.com/mcp"
fi

# 4. Install the agent skill (symlink tracks the repo)
mkdir -p "$HOME/.claude/skills"
if [ ! -e "$HOME/.claude/skills/vibe2fig" ]; then
  ln -s "$DIR/vibe2fig_skill" "$HOME/.claude/skills/vibe2fig"
  say "skill installed -> ~/.claude/skills/vibe2fig"
else
  say "skill already installed"
fi

say "done. Open Claude Code and say: \"turn this app into a Figma file\""
say "optional: install the UI/UX Pro Max skill for layout quality (recommended)"
