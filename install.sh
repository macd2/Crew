#!/bin/sh
# install.sh - thin wrapper: run the installer with the system python3.
exec python3 "$(dirname "$0")/install.py" "$@"
