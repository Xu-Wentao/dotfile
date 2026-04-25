# Add custom paths
fish_add_path ~/bin
fish_add_path ~/.local/bin
fish_add_path ~/usr/local/bin
fish_add_path /opt/homebrew/opt/python@3.14/bin

# Disable the greeting message
set -g fish_greeting

# Set your preferred editor
set -gx EDITOR vim

# Set proxy
set -gx https_proxy http://127.0.0.1:7897
set -gx http_proxy http://127.0.0.1:7897
set -gx all_proxy socks5://127.0.0.1:7897

# init starship
starship init fish | source

# alias
alias cc "claude"
alias rm "trash"
alias ll "ls -alt"
alias gs "git status"
alias cat "bat -p"
alias o "open"
alias rm "trash"
alias k "kubectl"

eval "$(/opt/homebrew/bin/brew shellenv fish)"
