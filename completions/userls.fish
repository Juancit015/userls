# Fish completions for userls.
#
# Installation:
#   packaged:  /usr/share/fish/vendor_completions.d/userls.fish
#   rootless:  ~/.config/fish/completions/userls.fish

# File completion is off by default; re-enabled where files are the argument.
complete -c userls -f

# Subcommands (only before one has been typed).
complete -c userls -n '__fish_use_subcommand' -a info -d 'show one account'
complete -c userls -n '__fish_use_subcommand' -a groups -d 'list groups or the groups of one account'
complete -c userls -n '__fish_use_subcommand' -a sessions -d 'list active login sessions'
complete -c userls -n '__fish_use_subcommand' -a export -d 'export the account list to a CSV file'

# Shared options, valid before and after the subcommand.
complete -c userls -s h -l help -d 'show the help message and exit'
complete -c userls -l json -d 'render the result as JSON on stdout'
complete -c userls -l csv -d 'render the result as CSV on stdout'
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
complete -c userls -n '__fish_seen_subcommand_from info groups' -f -a '(__userls_accounts)'

# export takes a file and accepts --force.
complete -c userls -n '__fish_seen_subcommand_from export' -l force -d 'overwrite an existing export file'
complete -c userls -n '__fish_seen_subcommand_from export' -F

function __userls_accounts
    set -l lines (command userls --csv 2>/dev/null)
    if test (count $lines) -lt 2
        return 0
    end
    for line in $lines[2..-1]
        set -l pieces (string split -n , -- $line)
        # fields 1 (name), 2 (uid) and the last one (type) survive a naive
        # split: only gecos, in the middle, may contain commas.
        if test (count $pieces) -ge 3; and string match -qr '^[0-9]+$' -- $pieces[2]
            printf '%s\tuid %s · %s\n' $pieces[1] $pieces[2] $pieces[-1]
        end
    end
end
