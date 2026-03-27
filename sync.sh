#!/bin/bash

DOTFILE_DIR="$HOME/Projects/github/dotfile"
LOG_FILE="$HOME/.dotfile_sync.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

cd "$DOTFILE_DIR" || { log "ERROR: Cannot cd to $DOTFILE_DIR"; exit 1; }

# Pull latest changes
log "Pulling from remote..."
git pull origin master >> "$LOG_FILE" 2>&1
PULL_STATUS=$?

if [ $PULL_STATUS -ne 0 ]; then
    log "ERROR: git pull failed (exit $PULL_STATUS)"
    exit 1
fi

# Stage all changes (tracked files only, no untracked)
git diff --quiet && git diff --cached --quiet
if [ $? -eq 0 ]; then
    log "No tracked changes to commit."
else
    git add -u
    git commit -m "auto sync: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE" 2>&1
    log "Committed tracked changes."
fi

# Push
git push origin master >> "$LOG_FILE" 2>&1
PUSH_STATUS=$?

if [ $PUSH_STATUS -ne 0 ]; then
    log "ERROR: git push failed (exit $PUSH_STATUS)"
    exit 1
fi

log "Sync complete."
