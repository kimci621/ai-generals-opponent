#!/bin/bash
# Запуск Zero Hour с модом Improved AI 1.2. Файлы мода кладутся в игру на время запуска,
# после выхода оригинал возвращается.
DIR="$(cd "$(dirname "$0")" && pwd)"
ZH="$DIR/GeneralsZH/Data"
MOD="$DIR/Mods/ImprovedAI_1.2/Data"
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
"$DIR/Запустить Zero Hour.command" "$@"
