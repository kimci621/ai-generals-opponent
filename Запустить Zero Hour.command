#!/bin/bash
# Запуск GeneralsX с данными игры из этой папки
DIR="$(cd "$(dirname "$0")" && pwd)"
export CNC_GENERALS_PATH="$DIR/Generals"
export CNC_GENERALS_ZH_PATH="$DIR/GeneralsZH"
exec "$DIR/GeneralsXZH.app/Contents/MacOS/run.sh" "$@"
