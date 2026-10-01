#!/bin/sh
# Point this clone's hooks at the versions kept in the repo.
set -eu
root=$(git rev-parse --show-toplevel)
for h in hooks/*; do
  [ -f "$h" ] || continue
  name=$(basename "$h")
  ln -sf "../../$h" "$root/.git/hooks/$name"
  chmod +x "$h"
  echo "installed $name"
done
