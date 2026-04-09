#!/bin/sh
input=$(cat)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // "unknown"')
model=$(echo "$input" | jq -r '.model.display_name // "unknown"')

# Context window: tokens used and total
ctx_input=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // empty')
ctx_total=$(echo "$input" | jq -r '.context_window.context_window_size // empty')
ctx_used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Rate limits (Claude.ai subscription)
five_hour_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
seven_day_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')

# Shorten home directory to ~
home="$HOME"
short_cwd=$(echo "$cwd" | sed "s|^$home|~|")

# Get git branch (skip locks)
branch=""
if git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1; then
  branch=$(git -C "$cwd" -c gc.auto=0 symbolic-ref --short HEAD 2>/dev/null)
fi

# ANSI colors (dim-friendly)
CYAN="\033[36m"
YELLOW="\033[33m"
GREEN="\033[32m"
BLUE="\033[34m"
MAGENTA="\033[35m"
RED="\033[31m"
RESET="\033[0m"

# Build directory + branch segment
if [ -n "$branch" ]; then
  dir_branch="${CYAN}${short_cwd}${RESET} ${YELLOW}${branch}${RESET}"
else
  dir_branch="${CYAN}${short_cwd}${RESET}"
fi

# Build context usage segment: "tokens_used/total (pct%)"
ctx_str=""
if [ -n "$ctx_input" ] && [ -n "$ctx_total" ]; then
  if [ -n "$ctx_used_pct" ]; then
    ctx_str="${GREEN}ctx:${ctx_input}/${ctx_total} ($(printf '%.0f' "$ctx_used_pct")%%)${RESET}"
  else
    ctx_str="${GREEN}ctx:${ctx_input}/${ctx_total}${RESET}"
  fi
elif [ -n "$ctx_used_pct" ]; then
  ctx_str="${GREEN}ctx:$(printf '%.0f' "$ctx_used_pct")%%${RESET}"
fi

# Build rate limit segments
quota_str=""
if [ -n "$five_hour_pct" ]; then
  quota_str="${quota_str}  ${YELLOW}5h:$(printf '%.0f' "$five_hour_pct")%%${RESET}"
fi
if [ -n "$seven_day_pct" ]; then
  quota_str="${quota_str}  ${MAGENTA}7d:$(printf '%.0f' "$seven_day_pct")%%${RESET}"
fi

# Assemble final output
usage_str=""
[ -n "$ctx_str" ] && usage_str="  ${ctx_str}"
usage_str="${usage_str}${quota_str}"

printf "${dir_branch}  ${BLUE}${model}${RESET}${usage_str}"
