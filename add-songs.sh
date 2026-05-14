#!/bin/bash
# Feelgram Music — Add Songs & Deploy Script
# Usage: ./add-songs.sh

set -e  # Exit on any error

# Absolute path to project (works no matter where you run from)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}♪ Feelgram Music — Songs Update & Deploy${NC}"
echo ""

# ── 1. Pre-flight checks ──────────────────────────────────────
if [ ! -d "music" ]; then
  echo -e "${RED}✗ music/ folder not found.${NC}"
  exit 1
fi

SONG_COUNT_BEFORE=$(jq 'reduce .[] as $f (0; . + ($f.songs | length))' playlist.json 2>/dev/null || echo "?")
FILE_COUNT=$(find music -maxdepth 1 -type f \( -iname '*.mp3' -o -iname '*.m4a' -o -iname '*.wav' -o -iname '*.ogg' -o -iname '*.flac' -o -iname '*.wmv' \) | wc -l | tr -d ' ')
MUSIC_SIZE=$(du -sh music | awk '{print $1}')

echo -e "${BOLD}Current state:${NC}"
echo "  • Songs in music/:    $FILE_COUNT"
echo "  • Songs in playlist:  $SONG_COUNT_BEFORE"
echo "  • Music folder size:  $MUSIC_SIZE"
echo ""

# Free port 8765 if something is using it
if lsof -ti:8765 > /dev/null 2>&1; then
  echo -e "${YELLOW}⚠  Port 8765 in use. Freeing...${NC}"
  lsof -ti:8765 | xargs kill -9 2>/dev/null || true
  sleep 1
fi

# ── 2. Start local server in background ───────────────────────
echo -e "${CYAN}▸ Starting local catalog server...${NC}"
python3 server.py > /tmp/feelgram-server.log 2>&1 &
SERVER_PID=$!

# Trap to always kill the server when the script exits (success OR error)
trap "kill $SERVER_PID 2>/dev/null || true" EXIT

# Wait for server (poll up to 10s)
WAITED=0
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/playlist 2>/dev/null | grep -q "200"; do
  if [ $WAITED -ge 10 ]; then
    echo -e "${RED}✗ Server didn't start within 10s. Check /tmp/feelgram-server.log${NC}"
    exit 1
  fi
  sleep 1
  WAITED=$((WAITED + 1))
done
echo -e "${GREEN}✓ Server ready${NC}"

# ── 3. Regenerate playlist.json ───────────────────────────────
echo -e "${CYAN}▸ Regenerating playlist.json...${NC}"
curl -s http://localhost:8765/api/playlist > playlist.json.tmp

# Validate JSON before replacing
if jq empty playlist.json.tmp 2>/dev/null; then
  mv playlist.json.tmp playlist.json
  SONG_COUNT_AFTER=$(jq 'reduce .[] as $f (0; . + ($f.songs | length))' playlist.json)
  FOLDER_COUNT=$(jq 'length' playlist.json)
  DIFF=$((SONG_COUNT_AFTER - ${SONG_COUNT_BEFORE//?/0}))
  [ "$SONG_COUNT_BEFORE" = "?" ] && DIFF="?" || DIFF=$((SONG_COUNT_AFTER - SONG_COUNT_BEFORE))
  echo -e "${GREEN}✓ playlist.json updated — $SONG_COUNT_AFTER songs in $FOLDER_COUNT folders${NC}"
  if [ "$DIFF" != "?" ] && [ "$DIFF" -gt 0 ]; then
    echo -e "${BOLD}  +$DIFF new songs detected${NC}"
  elif [ "$DIFF" != "?" ] && [ "$DIFF" -lt 0 ]; then
    echo -e "${YELLOW}  $DIFF songs removed${NC}"
  fi
else
  rm -f playlist.json.tmp
  echo -e "${RED}✗ Invalid JSON received from server${NC}"
  exit 1
fi

# Stop the server (trap will also catch this, but be explicit)
kill $SERVER_PID 2>/dev/null || true
trap - EXIT
sleep 1

# ── 4. Deploy to Netlify ──────────────────────────────────────
echo -e "${CYAN}▸ Deploying to Netlify...${NC}"
netlify deploy --prod --dir . 2>&1 | tail -8

echo ""
echo -e "${GREEN}${BOLD}✓ Done!${NC}"
echo -e "  ${BOLD}Next:${NC} Close the Feelgram PWA on your phone and reopen it to see new songs."
