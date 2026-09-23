#!/usr/bin/env bash
set -euo pipefail

# Crakbit Chain production source bootstrap.
# This creates a reproducible starting tree; it does NOT launch mainnet.

BITCOIN_TAG="v31.1"
RANDOMX_TAG="v1.2.3"
ROOT="${1:-crakbit-core-work}"

if [[ -e "$ROOT" ]]; then
  echo "Refusing to overwrite existing path: $ROOT" >&2
  exit 1
fi

mkdir -p "$ROOT"
cd "$ROOT"

echo "[1/4] Cloning Bitcoin Core ${BITCOIN_TAG}..."
git clone --depth 1 --branch "$BITCOIN_TAG" https://github.com/bitcoin/bitcoin.git crakbit-core

cd crakbit-core
UPSTREAM_COMMIT="$(git rev-parse HEAD)"
printf '%s\n' "$UPSTREAM_COMMIT" > ../BITCOIN_UPSTREAM_COMMIT.txt

# Preserve upstream as a named remote and rename origin for clarity.
git remote rename origin bitcoin-upstream
cd ..

echo "[2/4] Cloning RandomX ${RANDOMX_TAG}..."
git clone --depth 1 --branch "$RANDOMX_TAG" https://github.com/tevador/RandomX.git RandomX
cd RandomX
RANDOMX_COMMIT="$(git rev-parse HEAD)"
printf '%s\n' "$RANDOMX_COMMIT" > ../RANDOMX_UPSTREAM_COMMIT.txt
cd ..

echo "[3/4] Recording source manifest..."
cat > SOURCE_MANIFEST.txt <<EOF
bitcoin_tag=${BITCOIN_TAG}
bitcoin_commit=${UPSTREAM_COMMIT}
randomx_tag=${RANDOMX_TAG}
randomx_commit=${RANDOMX_COMMIT}
EOF

sha256sum SOURCE_MANIFEST.txt > SOURCE_MANIFEST.sha256

echo "[4/4] Done."
echo "Source root: $(pwd)"
echo "Bitcoin commit: ${UPSTREAM_COMMIT}"
echo "RandomX commit: ${RANDOMX_COMMIT}"
echo
echo "Next: apply the Crakbit consensus patch set only from a reviewed, versioned patch directory."
