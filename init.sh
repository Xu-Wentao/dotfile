#!/bin/bash

DOTFILE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

link() {
    local src="$1"
    local dst="$2"

    if [ -L "$dst" ]; then
        echo "EXISTS (symlink): $dst"
    elif [ -e "$dst" ]; then
        echo "BACKUP: $dst -> ${dst}.bak"
        mv "$dst" "${dst}.bak"
        ln -s "$src" "$dst"
        echo "LINKED: $dst -> $src"
    else
        ln -s "$src" "$dst"
        echo "LINKED: $dst -> $src"
    fi
}

# Link all dotfiles and dotdirs (excluding .git and non-dot files like init.sh/sync.sh)
for item in "$DOTFILE_DIR"/.*; do
    name="$(basename "$item")"
    # Skip . .. and .git
    [[ "$name" == "." || "$name" == ".." || "$name" == ".git" || "$name" == ".gitignore" ]] && continue
    link "$item" "$HOME/$name"
done

echo "Done."
