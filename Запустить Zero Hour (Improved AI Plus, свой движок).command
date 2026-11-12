#!/bin/bash
# Запуск Zero Hour со своим ИИ на своей сборке движка (ai-lab/GeneralsXZH-AI.app, захват техзданий умнее). Файлы мода кладутся в игру на время запуска,
# после выхода оригинал возвращается.
DIR="$(cd "$(dirname "$0")" && pwd)"
ZH="$DIR/GeneralsZH/Data"
MOD="$DIR/Mods/ImprovedAI_Plus/Data"
BACKUP="$DIR/Mods/vanilla_backup"

restore() {
    cp "$BACKUP/SkirmishScripts.scb" "$ZH/Scripts/SkirmishScripts.scb"
    rm -rf "$ZH/INI"
}
trap restore EXIT HUP INT TERM

# Оригинальный ИИ сохраняем один раз
mkdir -p "$BACKUP"
[ -f "$BACKUP/SkirmishScripts.scb" ] || cp "$ZH/Scripts/SkirmishScripts.scb" "$BACKUP/"

cp -R "$MOD/" "$ZH/"
"$DIR/ai-lab/scripts/run-ai.sh" "$@"
