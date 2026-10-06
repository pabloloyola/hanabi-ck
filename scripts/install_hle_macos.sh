#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HLE_DIR="$ROOT/.vendor/hanabi-learning-environment"
HLE_REV="54e79594f4b6fb40ebb3004289c6db0e34a8b5fb"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This helper is for macOS. See README.md for the HLE reference backend."
  exit 2
fi

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" ]]; then
  echo "Expected Apple Silicon (arm64), found: $ARCH"
  exit 2
fi

cd "$ROOT"
uv sync --extra dev
uv pip install --python "$ROOT/.venv/bin/python" \
  scikit-build cmake ninja cffi setuptools wheel

mkdir -p "$ROOT/.vendor"
if [[ ! -d "$HLE_DIR/.git" ]]; then
  git clone https://github.com/google-deepmind/hanabi-learning-environment.git "$HLE_DIR"
fi

git -C "$HLE_DIR" fetch origin "$HLE_REV"
git -C "$HLE_DIR" checkout "$HLE_REV"
rm -rf "$HLE_DIR/_skbuild"

CMAKE_ARGS="-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5" \
uv pip install \
  --python "$ROOT/.venv/bin/python" \
  --no-build-isolation \
  "$HLE_DIR"

uv run python - <<'PY'
from hanabi_learning_environment import pyhanabi

assert pyhanabi.cdef_loaded(), "HLE CFFI declarations did not load"
assert pyhanabi.lib_loaded(), "HLE native library did not load"

game = pyhanabi.HanabiGame({
    "players": 2,
    "seed": 0,
    "random_start_player": False,
})
state = game.new_initial_state()
while state.cur_player() == pyhanabi.CHANCE_PLAYER_ID:
    state.deal_random_card()

assert state.cur_player() == 0
assert state.deck_size() == 40
print("HLE OK: native library loaded; 2p seed-0 deck size =", state.deck_size())
PY

echo
echo "Run parity checks with:"
echo "  uv run pytest tests/test_backends.py -v"
