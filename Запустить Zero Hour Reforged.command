#!/bin/bash
# Zero Hour Reforged: отдельный движок из ~/Games/Generals-Reforged, данные игры из этой папки.
# Папку базовой Generals игра берёт из Registry.ini в своей папке настроек.
# Не запускать одновременно с ярлыками Improved AI: они подменяют файлы в GeneralsZH.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$HOME/Games/Generals-Reforged/build-mac/Zero Hour Reforged.app/Contents/MacOS/generals" -root "$DIR/GeneralsZH" "$@"
