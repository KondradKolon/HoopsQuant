#!/usr/bin/env bash
set -euo pipefail

# Incremental runner for Odds API ingestion.
#
# This script is intentionally robust against SQLAlchemy echo logs on stdout:
# it parses ONLY lines starting with START_ISO= / END_ISO=.

DAYS=7
BUFFER_DAYS=1
MAX_GAMES=100
SLEEP_SEC="${ODDS_API_SLEEP_SEC:-0.1}"
FALLBACK_START=""
DEBUG=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  ./run_incremental_odds_fetch.sh [options]

Options:
  --days N            Days forward to fetch (default: 3)
  --buffer-days N     Days to subtract from last odds date (default: 1)
  --max-games N       Cap number of games processed (default: 45)
  --sleep-sec S       Sleep between games (default: ODDS_API_SLEEP_SEC or 0.1)
  --fallback-start D  YYYY-MM-DD used when DB has no odds yet
  --debug             Enable debug logs in odds client
  --dry-run           Print computed range and exit
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days) DAYS="$2"; shift 2 ;;
    --buffer-days) BUFFER_DAYS="$2"; shift 2 ;;
    --max-games) MAX_GAMES="$2"; shift 2 ;;
    --sleep-sec) SLEEP_SEC="$2"; shift 2 ;;
    --fallback-start) FALLBACK_START="$2"; shift 2 ;;
    --debug) DEBUG=1; shift 1 ;;
    --dry-run) DRY_RUN=1; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-./venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "No python found. Set PYTHON_BIN or install python3." >&2
    exit 1
  fi
fi

range_args=(
  --days "$DAYS"
  --buffer-days "$BUFFER_DAYS"
)

if [[ -n "$FALLBACK_START" ]]; then
  range_args+=(--fallback-start "$FALLBACK_START")
fi

range_out=$($PYTHON_BIN get_odds_fetch_range.py "${range_args[@]}" | tr -d '\r')

START_ISO=$(printf '%s\n' "$range_out" | awk -F= '/^START_ISO=/{print $2; exit}')
END_ISO=$(printf '%s\n' "$range_out" | awk -F= '/^END_ISO=/{print $2; exit}')

if [[ -z "${START_ISO:-}" || -z "${END_ISO:-}" ]]; then
  echo "Failed to parse START_ISO/END_ISO from get_odds_fetch_range.py output:" >&2
  printf '%s\n' "$range_out" >&2
  exit 1
fi

echo "Range: $START_ISO  ->  $END_ISO"

if [[ "$DRY_RUN" -eq 1 ]]; then
  exit 0
fi

odds_args=(
  --start "$START_ISO"
  --end "$END_ISO"
  --max-games "$MAX_GAMES"
  --sleep-sec "$SLEEP_SEC"
)

if [[ "$DEBUG" -eq 1 ]]; then
  odds_args+=(--debug)
fi

$PYTHON_BIN odds_api_client.py "${odds_args[@]}"
