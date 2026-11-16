#!/usr/bin/env python3
"""Темп бота Improved AI Plus из одного места.

Темп - одно число в процентах: 100 = исходная версия, 110 = всё на 10% медленнее, 90 = на 10% быстрее.
Хранится в Mods/ImprovedAI_Plus/tempo.json. Скрипты всегда пересчитываются от исходного текста
Mods/ImprovedAI_Plus/SkirmishScripts.base.txt (темп 100), ошибки округления не копятся.

    python3 -I tools/ai_tempo.py show          текущий темп
    python3 -I tools/ai_tempo.py slow 10       замедлить на 10% (темп x1.1)
    python3 -I tools/ai_tempo.py fast 10       ускорить на 10% (темп /1.1, отменяет slow 10)
    python3 -I tools/ai_tempo.py set 110       задать темп прямо
    python3 -I tools/ai_tempo.py check         самопроверка: темп 100 по смыслу равен исходному, 110 масштабирует

Что меняется при темпе P:
- эскалация (_ESCALATION, от неё волны атак, суперорудие, расширения, отказ от захвата): прибавка за шаг
  времени в скриптах "* Time Escalation*" 1 -> 100, остальные прибавки и все пороги x P, то есть счётчик
  растёт как при шаге 7 * P / 100 секунд;
- таймеры скриптов в секундах (SET_MILLISECOND_TIMER, SET_RANDOM_MSEC_TIMER, SET_RANDOM_TIMER) x P / 100;
- командир в движке: счётчик _AILAB_TEMPO = P, движок умножает на P / 100 период проверки (5 с) и паузу
  между атаками (45 с). Пересборка движка не нужна.
Не меняется: SET_TIMER (флажки на 1 кадр), delaySeconds (частота проверки условий), скорость постройки и юниты.

Правки скриптов делать в SkirmishScripts.base.txt, потом запустить `set <текущий темп>`.
SkirmishScripts.txt и Data/Scripts/SkirmishScripts.scb - результат, руками не править.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

G = Path(__file__).resolve().parent.parent
MOD = G / 'Mods/ImprovedAI_Plus'
BASE, TXT, SCB, STATE = MOD / 'SkirmishScripts.base.txt', MOD / 'SkirmishScripts.txt', MOD / 'Data/Scripts/SkirmishScripts.scb', MOD / 'tempo.json'
TIMERS = ('SET_MILLISECOND_TIMER', 'SET_RANDOM_MSEC_TIMER', 'SET_RANDOM_TIMER')


def scale(lines, P):
    """Текст скриптов при темпе P (проценты)."""
    L = list(lines); script = ''
    for i, l in enumerate(L):
        m = re.match(r'\s*name s "(.*)"', l)
        if m: script = m[1]
        m = re.match(r'\s*name key "(\w+)"', l)
        if not m: continue
        key = m[1]; ps = []; j = i + 2
        while j < len(L) and L[j].strip().startswith('param '): ps.append(j); j += 1
        names = ' '.join(L[p] for p in ps)

        def mul(p, f, real=False):
            t = L[p].split(' '); k = t.index('param')
            if real or t[k + 1] == 'REAL':
                assert t[k + 1] == 'REAL'; t[k + 3] = f'{round(float(t[k + 3]) * f, 3):g}'
            else:
                assert t[k + 1] == 'INT' and t[k + 3] == '0', L[p]; t[k + 2] = str(round(int(t[k + 2]) * f))
            L[p] = ' '.join(t)

        ints = [p for p in ps if L[p].strip().startswith('param INT')]
        if '"_ESCALATION"' in names and key == 'INCREMENT_COUNTER':
            mul(ints[0], 100 if 'Time Escalation' in script else P)
        elif '"_ESCALATION"' in names and key == 'COUNTER':
            mul(ints[0], P)
        elif '"_AILAB_TEMPO"' in names and key == 'SET_COUNTER':
            assert L[ints[0]].strip() == 'param INT 100 0 ""'; mul(ints[0], P / 100)
        elif key in TIMERS:
            for p in ps[1:]: mul(p, P / 100)
    return L


def build(P):
    L = scale(BASE.read_text(encoding='latin1').split('\n'), P)
    TXT.write_text('\n'.join(L), encoding='latin1')
    subprocess.run([sys.executable, '-I', str(G / 'tools/scb.py'), 'build', str(TXT), str(SCB)], check=True)
    subprocess.run([sys.executable, '-I', str(G / 'tools/scb.py'), 'check', str(SCB)], check=True)
    STATE.write_text(json.dumps({'tempo': P}) + '\n')
    shutil.rmtree(G / 'ai-lab/data/improved_ai_plus', ignore_errors=True)  # полигон пересоздаст клон
    print(f'темп {P}%: шаг эскалации {7 * P / 100:g} с, пауза командира {45 * P / 100:g} с')


def check():
    base = BASE.read_text(encoding='latin1').split('\n')
    # темп 100 по смыслу равен исходному: эскалация вся x100 (целые проценты), таймеры те же числа
    for a, b in zip(base, scale(base, 100)):
        if a == b: continue
        ta, tb = a.split(), b.split()
        assert ta[1] == tb[1] and (int(tb[2]) == 100 * int(ta[2]) if ta[1] == 'INT' else float(tb[3]) == float(ta[3])), (a, b)
    s = scale(base, 110)
    diff = [(a.strip(), b.strip()) for a, b in zip(base, s) if a != b]
    assert ('param INT 15 0 ""', 'param INT 1650 0 ""') in diff, 'порог эскалации x110'
    assert ('param REAL 0 4e+01 ""', 'param REAL 0 44 ""') in diff, 'таймер x1.1'
    assert ('param INT 100 0 ""', 'param INT 110 0 ""') in diff, 'счётчик _AILAB_TEMPO'
    assert ('param INT 1 0 ""', 'param INT 100 0 ""') in diff, 'шаг времени эскалации x100'
    print('ok,', len(diff), 'строк меняется при темпе 110')


def main(a):
    cur = json.loads(STATE.read_text())['tempo'] if STATE.exists() else 100
    if a == ['show']: print(f'темп {cur}%'); return
    if a == ['check']: check(); return
    if len(a) == 2 and a[0] in ('slow', 'fast', 'set'):
        x = float(a[1])
        P = {'slow': cur * (1 + x / 100), 'fast': cur / (1 + x / 100), 'set': x}[a[0]]
        P = round(P)
        if not 20 <= P <= 500: sys.exit(f'темп {P}% вне 20-500')
        build(P); return
    sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
