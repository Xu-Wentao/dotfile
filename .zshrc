# Path to your oh-my-zsh installation.
export ZSH="/Users/xuwentao/.oh-my-zsh"

# kubernetes
export KUBECONFIG="/Users/xuwentao/.kube/config"

# GO
export GOPATH="/Users/xuwentao/go"
export GO111MODULE="on"
export GOBIN=$GOPATH/bin
export PATH=$PATH:$GOPATH:$GOBIN
export GOPROXY="https://goproxy.cn,direct"
export GOPRIVATE="code.srdcloud.cn"

export PATH="/usr/local/sbin:$PATH"
export PATH="/user/local/Cellar:$PATH"
export PATH="/usr/local/go:$PATH"
export HOMEBREW_NO_AUTO_UPDATE=true
export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"
export PATH="/Users/xuwentao/.local/bin:$PATH"
export JAVA_HOME="/Library/Java/JavaVirtualMachines/jdk-1.8.jdk/Contents/Home"
export PATH="${JAVA_HOME}/bin:${PATH}"
export PATH="$(brew --prefix coreutils)/libexec/gnubin:/usr/local/bin:$PATH"

export PATH="/usr/local/opt/openssl@1.1/bin:$PATH"
export PATH="/usr/local/opt/ncurses/bin:$PATH"
export PATH="/opt/homebrew/bin/:$PATH"

export HOMEBREW_PREFIX="/opt/homebrew"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# cargo
export PATH=/Users/xuwentao/.cargo/bin:$PATH

# git lfs
export GIT_LFS_SKIP_SMUDGE=1

# zsh-nvm lazy load
export NVM_LAZY_LOAD=true

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/robbyrussell/oh-my-zsh/wiki/Themes
ZSH_THEME="powerlevel10k/powerlevel10k"
# ZSH_THEME="ys"

# Which plugins would you like to load?
# Standard plugins can be found in ~/.oh-my-zsh/plugins/*
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(
	zsh-autosuggestions 
	zsh-syntax-highlighting
)

source $ZSH/oh-my-zsh.sh
# source ~/.bash_profile
source $HOMEBREW_PREFIX/share/zsh-autocomplete/zsh-autocomplete.plugin.zsh
source $HOMEBREW_PREFIX/share/powerlevel10k/powerlevel10k.zsh-theme

alias rm="trash"
alias cc="gcc-10"
alias cxx="g++-10"
alias gcc="gcc-10"
alias g++="g++-10"
alias c++="g++-10"
alias go-linux="CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go"
alias o="open"
alias gs="git status"
alias tree="tree -L 1"
alias ll="ls -al -h"
alias 翻译='fy'
alias ..='cd ..'
alias k='kubectl'
alias cat='bat -p'
alias sed='gsed'
alias vim='nvim'

source <(helm completion zsh)
