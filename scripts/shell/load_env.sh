#!/usr/bin/env bash

# PURPOSE: Robustly export key=value pairs from a .env file into the current shell
# DEPENDENCIES: bash
# MODIFICATION NOTES: v2 - enable extglob, avoid value expansion, handle quotes, CR-stripping

set -euo pipefail
shopt -s extglob

ENV_FILE="${1:-/opt/Archivist/.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "load_env.sh: env file not found: $ENV_FILE" >&2
  exit 1
fi

# Strip CRs to be safe, then iterate
while IFS= read -r line; do
  # Trim leading/trailing whitespace
  line="${line##+([[:space:]])}"
  line="${line%%+([[:space:]])}"
  # Skip blanks and comments
  [ -z "$line" ] && continue
  [[ "$line" == \#* ]] && continue
  # Require key=value
  [[ "$line" != *"="* ]] && continue

  key="${line%%=*}"
  val="${line#*=}"

  # Trim around key/val
  key="${key##+([[:space:]])}"
  key="${key%%+([[:space:]])}"
  val="${val##+([[:space:]])}"
  val="${val%%+([[:space:]])}"

  # Remove one layer of surrounding quotes if present
  if [[ "$val" =~ ^".*"$ ]]; then
    val="${val:1:${#val}-2}"
  elif [[ "$val" =~ ^'.*'$ ]]; then
    val="${val:1:${#val}-2}"
  fi

  # Assign without eval and without expanding $ inside value
  printf -v "$key" '%s' "$val"
  export "$key"
done < <(sed -e 's/\r$//' "$ENV_FILE")

exit 0


