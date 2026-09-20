# label50 — human ground truth

50 случайных deg=1 нод (seed 42). Разметка по исходникам: **6 missing_edge / 44 correct_leaf**.

## Метрики авто-классификатора (pre-pass) по человеческой разметке

| метрика | значение |
|---|---|
| precision (missing_edge) | 20% (5/25) |
| recall (missing_edge) | 83% (5/6) |
| accuracy | 58% (28/50) |

## 6 пропущенных рёбер (все — типы, не моделируемые символьным линкером)


| # | нода | пропущенное ребро | тип |
|---|---|---|---|
| 4 | STOP (lifecycle.test.js L20) | lifecycle.test.js → skills_brainstorming_scripts_stop_server (path.join → stop-server.sh, use L185) | path-string file ref |
| 7 | Executing Plans Skill (RELEASE-NOTES) | release_notes → skills_executing_plans_skill_file (mentions; file-нод существует) | doc→file mention |
| 15 | src (helper.test.js L15) | helper.test.js → skills_brainstorming_scripts_helper (fs.readFileSync(HELPER=helper.js)) | path-string file ref |
| 24 | cleanup_test_env() (setup.sh L77) | test-bootstrap-caching.sh / test-plugin-loading.sh / test-priority.sh → setup.sh (`source` + `trap cleanup_test_env EXIT`) | cross-file sh symbol |
| 35 | packageJsonPath (test-pi-extension.mjs L10) | test-pi-extension.mjs → package (root package.json node) | path-string file ref |
| 42 | OPENCODE_CONFIG_DIR (setup.sh L14) | test-plugin-loading.sh / test-priority.sh → setup.sh (используют переменную, установленную source'ом) | cross-file sh var |

## 25 false positives авто-классификатора (помечены missing_edge, по факту correct_leaf)

Общий паттерн: локальные символы, используемые **внутри одного файла** (makeHarness x8, debounceTimers, SUPERPOWERS_VERSION, pluginURL, unknownChild, assertMappingConstants), stdlib-импорты (path, crypto, shutil) или doc-секции с единственной связью на родной файл. Авто-классификатор видел «у ноды 1 ребро + есть code-символ» и предсказывал пропуск; символьный линкер корректно не строит intra-file рёбер.

## 1 false negative
#7 — RELEASE-NOTES секция 'Executing Plans Skill': авто-классификатор увидел concept-лист (references → release_notes), не проверив, что file-нод `skills_executing_plans_skill_file` существует и mentions-ребра нет.

## Вывод для линкера

- Размеченный precision символьного линкера на выборке: **100%** (0 ложных рёбер среди 44 correct_leaf — ни один не должен был получать ребро и не получил).
- Recall на выборке: **0/6** — все 6 пропусков лежат в классах рёбер, отсутствующих в ТЗ линкера: path-строковые file-refs, cross-file sh-символы/переменные, doc→file mentions из release-notes.
- Следующая итерация пост-прохода: паттерны `path.join(...,'x.ext')`/`fs.readFileSync(CONST)` → references на file-нод; sh `source` + используемые переменные/функции; mentions только по существующим file-нодам.
