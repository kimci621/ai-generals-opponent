#!/bin/bash
# Запуск своей сборки GeneralsXZH-AI.app на данных установки. Аналог «Запустить Zero Hour.command».
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export CNC_GENERALS_PATH="${CNC_GENERALS_PATH:-$ROOT/Generals}"
export CNC_GENERALS_ZH_PATH="${CNC_GENERALS_ZH_PATH:-$ROOT/GeneralsZH}"
exec "$ROOT/ai-lab/GeneralsXZH-AI.app/Contents/MacOS/run.sh" "$@"
