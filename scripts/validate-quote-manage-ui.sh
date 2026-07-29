#!/usr/bin/env bash
# Back-compat wrapper: full custom_addons validation lives in validate-custom-addons.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$ROOT/scripts/validate-custom-addons.sh"
