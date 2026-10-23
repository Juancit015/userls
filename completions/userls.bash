# Bash completion for userls.
#
# Installation:
#   packaged:  /usr/share/bash-completion/completions/userls
#   rootless:  ~/.local/share/bash-completion/completions/userls

# Account names for the subcommands that take one, silent on any failure.
_userls_accounts() {
    command userls --json 2>/dev/null | python3 -c '
import json, sys
try:
    payload = json.load(sys.stdin)
except (OSError, ValueError):
    raise SystemExit(0)
for account in payload.get("accounts", []):
    print(account["name"], account["uid"], account["type"], sep="\t")
' 2>/dev/null | while IFS=$'\t' read -r name _uid _type; do
        printf '%s\n' "$name"
    done
}

_userls() {
    local cur prev word sub=""
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local subcommands="info groups perms sessions"
    local options="--json --no-color --type --search --version --help -h"

    for word in "${COMP_WORDS[@]:1:COMP_CWORD-1}"; do
        case "$word" in
            info|groups|perms|sessions) sub="$word" ;;
        esac
    done

    if [[ $prev == --type ]]; then
        COMPREPLY=($(compgen -W "all normal service system unknown" -- "$cur"))
        return
    fi

    if [[ $cur == -* ]]; then
        COMPREPLY=($(compgen -W "$options" -- "$cur"))
        return
    fi

    case "$sub" in
        info|groups|perms)
            COMPREPLY=($(compgen -W "$(_userls_accounts)" -- "$cur"))
            ;;
        *)
            COMPREPLY=($(compgen -W "$subcommands" -- "$cur"))
            ;;
    esac
}

complete -F _userls userls
