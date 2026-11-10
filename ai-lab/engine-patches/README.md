# Правки движка GeneralsX для полигона

Сам движок в репозиторий не входит: это клон https://github.com/fbraz3/GeneralsX в `ai-lab/engine/GeneralsX`, ветка `ai-lab`. Здесь лежат наши коммиты поверх него.

Основа: коммит `ddbfd13aea5bc9484bb7b16768fb8371751e1621` upstream.

Восстановить:

```
git clone https://github.com/fbraz3/GeneralsX.git ai-lab/engine/GeneralsX
cd ai-lab/engine/GeneralsX
git checkout -b ai-lab ddbfd13aea5bc9484bb7b16768fb8371751e1621
git am ../../engine-patches/*.patch
```

Потом `ai-lab/scripts/build-ai-app.sh`. Обновить патчи после новых коммитов в движке:
`git -C ai-lab/engine/GeneralsX format-patch -o ../../engine-patches ddbfd13..ai-lab` (старые файлы перед этим удалить).
