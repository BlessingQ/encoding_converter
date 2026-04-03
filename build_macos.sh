#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

ARGS=(
  -m PyInstaller
  --noconfirm
  --clean
  --windowed
  --onedir
  --name ENCConverter
  --osx-bundle-identifier com.encconverter.app
  --collect-all tkinterdnd2
  gui.py
)

if [[ -f "assets/icon.png" ]]; then
  ARGS+=(--icon assets/icon.png --add-data assets/icon.png:assets)
fi

python3 "${ARGS[@]}"

echo
echo "Build complete:"
echo "  dist/ENCConverter.app"
