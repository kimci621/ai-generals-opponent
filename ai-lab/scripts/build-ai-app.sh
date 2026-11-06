#!/usr/bin/env bash
# Сборка движка из ai-lab/engine/GeneralsX и упаковка в ai-lab/GeneralsXZH-AI.app.
# Оригинальный GeneralsXZH.app не трогает.
set -euo pipefail

LAB="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="$LAB/engine/GeneralsX"
APP="$LAB/GeneralsXZH-AI.app"
ZIP="$ENGINE/macos-arm64-GeneralsXZH.zip"

# Те же переменные, что у CI проекта (.github/workflows/build-macos.yml)
export VCPKG_ROOT="${VCPKG_ROOT:-$HOME/vcpkg}"
export VCPKG_DEFAULT_TRIPLET=arm64-osx
export VULKAN_SDK="${VULKAN_SDK:-$HOME/VulkanSDK/1.4.341.1/macOS}"
export OPENSSL_ROOT_DIR="${OPENSSL_ROOT_DIR:-$(brew --prefix openssl@3)}"

cd "$ENGINE"
if [[ -f build/macos-vulkan/CMakeCache.txt ]]; then
    ./scripts/build/macos/build-macos-zh.sh --build-only
else
    ./scripts/build/macos/build-macos-zh.sh
fi
./scripts/build/macos/bundle-macos-zh.sh

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"
rm -rf "$APP"
mv "$TMP/GeneralsXZH.app" "$APP"
rm -f "$ZIP"
echo "Готово: $APP"
