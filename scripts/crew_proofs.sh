#!/bin/sh
# crew_proofs.sh - run every crew proof with the profile's own python3.
#
# --quiet: say nothing when everything passes, so the nightly job posts into the alert topic only
# when a proof actually broke.
exec python3 "$(dirname "$0")/crew_proofs.py" --quiet "$@"
