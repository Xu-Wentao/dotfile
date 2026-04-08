# Snapshot file
# Unset all aliases to avoid conflicts with functions
unalias -a 2>/dev/null || true
# Functions
# Shell Options
setopt nohashdirs
setopt login
# Aliases
alias -- 翻译=fy
alias -- ..='cd ..'
alias -- c++=g++-10
alias -- cat='bat -p'
alias -- cc=gcc-10
alias -- cxx=g++-10
alias -- g++=g++-10
alias -- gcc=gcc-10
alias -- go-linux='CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go'
alias -- gs='git status'
alias -- k=kubectl
alias -- ll='ls -al -h'
alias -- o=open
alias -- rm=trash
alias -- run-help=man
alias -- sed=gsed
alias -- tree='tree -L 1'
alias -- vim=nvim
alias -- which-command=whence
# Check for rg availability
if ! (unalias rg 2>/dev/null; command -v rg) >/dev/null 2>&1; then
  function rg {
  local _cc_bin="${CLAUDE_CODE_EXECPATH:-}"
  [[ -x $_cc_bin ]] || _cc_bin=$(command -v claude 2>/dev/null)
  if [[ ! -x $_cc_bin ]]; then command rg "$@"; return; fi
  if [[ -n $ZSH_VERSION ]]; then
    ARGV0=rg "$_cc_bin" "$@"
  elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    ARGV0=rg "$_cc_bin" "$@"
  elif [[ $BASHPID != $$ ]]; then
    exec -a rg "$_cc_bin" "$@"
  else
    (exec -a rg "$_cc_bin" "$@")
  fi
}
fi
export PATH=/opt/homebrew/opt/python@3.14/bin:/Users/xuwentao/.local/bin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/opt/pkg/env/active/bin:/opt/pmk/env/global/bin:/opt/homebrew/bin:/Applications/Ghostty.app/Contents/MacOS
