# Fish completions for userls.
#
# Installation:
#   packaged:  /usr/share/fish/vendor_completions.d/userls.fish
#   rootless:  ~/.config/fish/completions/userls.fish

# File completion is off by default; the arguments are account names.
complete -c userls -f

# Subcommands (only before one has been typed).
complete -c userls -n '__fish_use_subcommand' -a info -d 'show one account'
complete -c userls -n '__fish_use_subcommand' -a groups -d 'list groups or the groups of one account'
complete -c userls -n '__fish_use_subcommand' -a perms -d 'show group-derived privilege levels'
complete -c userls -n '__fish_use_subcommand' -a sessions -d 'list active login sessions'

# Shared options, valid before and after the subcommand.
complete -c userls -s h -l help -d 'show the help message and exit'
complete -c userls -l json -d 'render the result as JSON on stdout'
complete -c userls -l no-color -d 'disable ANSI color'
complete -c userls -l version -d 'show the program version and exit'
complete -c userls -l search -d 'search accounts by name (substring) or by UID (exact)'

complete -c userls -l type -x -a all -d 'every account'
complete -c userls -l type -x -a normal -d 'human account with a login shell and home directory'
complete -c userls -l type -x -a service -d 'service account (non-login shell or bogus home)'
complete -c userls -l type -x -a system -d 'system account (root or the system UID range)'
complete -c userls -l type -x -a unknown -d 'account outside every configured range'
# Keep this entry last: the option description is taken from the final
# matching definition, while each value keeps its own candidate description.
complete -c userls -l type -x -d 'filter accounts by type'

# Live account names for the subcommands that take one.
complete -c userls -n '__fish_seen_subcommand_from info groups perms' -f -a '(__userls_accounts)'

function __userls_accounts
    command userls --json 2>/dev/null | python3 -c '
import json, sys
try:
    payload = json.load(sys.stdin)
except (OSError, ValueError):
    raise SystemExit(0)
for account in payload.get("accounts", []):
    print("%s\tuid %s · %s" % (account["name"], account["uid"], account["type"]))
' 2>/dev/null
end
