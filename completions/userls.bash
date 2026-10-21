# Bash completion for userls.
#
# Installation:
#   packaged:  /usr/share/bash-completion/completions/userls
#   rootless:  ~/.local/share/bash-completion/completions/userls

# Account names for the subcommands that take one, silent on any failure.
_userls_accounts() {
    command userls --csv 2>/dev/null | while IFS=, read -r name uid _; do
        [[ $uid =~ ^[0-9]+$ ]] || continue  # skips the CSV header
        printf '%s\n' "$name"
    done
}

_userls() {
    local cur prev word sub=""
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local subcommands="info groups sessions export"
    local options="--json --csv --no-color --type --search --version --help -h"

    for word in "${COMP_WORDS[@]:1:COMP_CWORD-1}"; do
        case "$word" in
            info|groups|sessions|export) sub="$word" ;;
        esac
    done

    if [[ $prev == --type ]]; then
        COMPREPLY=($(compgen -W "all normal service system unknown" -- "$cur"))
        return
    fi

    if [[ $cur == -* ]]; then
        COMPREPLY=($(compgen -W "$options" -- "$cur"))
        if [[ $sub == export ]]; then
            COMPREPLY+=($(compgen -W "--force" -- "$cur"))
        fi
        return
    fi

    case "$sub" in
        info|groups)
            COMPREPLY=($(compgen -W "$(_userls_accounts)" -- "$cur"))
            ;;
        export)
            compopt -o filenames 2>/dev/null
            COMPREPLY=($(compgen -f -- "$cur"))
            ;;
        *)
            COMPREPLY=($(compgen -W "$subcommands" -- "$cur"))
            ;;
    esac
}

complete -F _userls userls
