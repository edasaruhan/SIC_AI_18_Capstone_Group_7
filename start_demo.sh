#!/usr/bin/env bash
set -eu
PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
for python_command in "$PROJECT_DIR/.venv/bin/python" python3.12 python3 python; do
    if command -v "$python_command" >/dev/null 2>&1 && "$python_command" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)' >/dev/null 2>&1; then
        exec "$python_command" "$PROJECT_DIR/tools/start_demo.py" "$@"
    fi
done
printf '%s\n' 'Python 3.12 is required. Install it, then run this launcher again.' >&2
exit 1
