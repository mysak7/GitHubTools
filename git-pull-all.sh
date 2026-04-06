#!/bin/bash

# Find all git repos under the given path (default: current dir)
ROOT="${1:-..}"

find "$ROOT" -name ".git" -type d | sort | while IFS= read -r gitdir; do
    dir="${gitdir%/.git}"

    result=$(git -C "$dir" pull 2>&1)
    code=$?

    if [[ "$result" == *"Already up to date"* ]]; then
        : # nothing to report
    elif [[ "$result" == *"CONFLICT"* ]] || [[ "$result" == *"conflict"* ]]; then
        echo "OK [CONFLICT] $dir"
        echo "  $result" | sed 's/^/    /'
    elif [[ $code -ne 0 ]]; then
        : # pull failed (no remote, auth error, etc.) — silent
    else
        echo "OK $dir"
    fi
done
