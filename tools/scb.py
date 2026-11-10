# Конвертер скриптов ИИ (.scb, формат CkMp) в текст и обратно.
#   python3 -I tools/scb.py dump  <файл.scb> <файл.txt>
#   python3 -I tools/scb.py build <файл.txt> <файл.scb>
#   python3 -I tools/scb.py check <файл.scb>...   кругооборот scb -> txt -> scb, побайтно
# Формат взят из GeneralsX: DataChunk.cpp (заголовки, словари), Scripts.cpp (скрипты), SidesList.cpp (игроки, команды).
# Текст: строка = отступ + ключ + значения. Типы полей записаны в тексте, поэтому build схему не знает.
# Новое имя (метка блока, ключ словаря, имя условия) build сам добавит в таблицу имён.
import json, re, struct, sys

PARAM_TYPES = ("INT REAL SCRIPT TEAM COUNTER FLAG COMPARISON WAYPOINT BOOLEAN TRIGGER_AREA TEXT_STRING SIDE SOUND "
               "SCRIPT_SUBROUTINE UNIT OBJECT_TYPE COORD3D ANGLE TEAM_STATE RELATION AI_MOOD DIALOG MUSIC MOVIE "
               "WAYPOINT_PATH LOCALIZED_TEXT BRIDGE KIND_OF_PARAM ATTACK_PRIORITY_SET RADAR_EVENT_TYPE SPECIAL_POWER "
               "SCIENCE UPGRADE COMMANDBUTTON_ABILITY BOUNDARY BUILDABLE SURFACES_ALLOWED SHAKE_INTENSITY COMMAND_BUTTON "
               "FONT_NAME OBJECT_STATUS COMMANDBUTTON_ALL_ABILITIES SKIRMISH_WAYPOINT_PATH COLOR EMOTICON OBJECT_PANEL_FLAG "
               "FACTION_NAME OBJECT_TYPE_LIST REVEALNAME SCIENCE_AVAILABILITY LEFT_OR_RIGHT PERCENT").split()
COORD3D = PARAM_TYPES.index("COORD3D")
DICT_TYPES = ("bool", "int", "real", "str", "ustr")
# блоки, у которых после полей идут вложенные блоки
CONTAINERS = {"PlayerScriptsList", "ScriptList", "ScriptGroup", "Script", "OrCondition"}


def qs(b: bytes) -> str:
    return json.dumps(b.decode("latin1"))


def fmt_real(b: bytes) -> str:
    # самая короткая запись, которая даёт те же 4 байта; иначе hex
    v = struct.unpack("<f", b)[0]
    for p in range(1, 10):
        s = "%.*g" % (p, v)
        try:
            if struct.pack("<f", float(s)) == b:
                return s
        except (OverflowError, ValueError):
            break
    return "0x" + b.hex()


class Reader:
    def __init__(self, d, toc):
        self.d, self.p, self.toc = d, 0, toc

    def take(self, n):
        b = self.d[self.p:self.p + n]
        if len(b) != n:
            raise ValueError(f"конец данных на {self.p}")
        self.p += n
        return b

    def i32(self): return struct.unpack("<i", self.take(4))[0]
    def u8(self): return self.take(1)[0]
    def real(self): return fmt_real(self.take(4))
    def s(self): return qs(self.take(struct.unpack("<H", self.take(2))[0]))

    def us(self):
        n = struct.unpack("<H", self.take(2))[0]
        return json.dumps(self.take(2 * n).decode("utf-16-le"))

    def key(self):
        kt = self.i32()
        return f"{json.dumps(self.toc[kt >> 8])} {kt & 0xff}"


def dump_dict(r, out, ind):
    n = struct.unpack("<H", r.take(2))[0]
    out.append(f"{ind}dict {n}")
    for _ in range(n):
        kt = r.i32()
        t = kt & 0xff
        val = {0: lambda: str(r.u8()), 1: lambda: str(r.i32()), 2: r.real, 3: r.s, 4: r.us}[t]()
        out.append(f"{ind}  {json.dumps(r.toc[kt >> 8])} {DICT_TYPES[t]} {val}")


def dump_param(r, out, ind):
    t = r.i32()
    name = PARAM_TYPES[t] if 0 <= t < len(PARAM_TYPES) else str(t)
    if t == COORD3D:
        out.append(f"{ind}param {name} {r.real()} {r.real()} {r.real()}")
    else:
        out.append(f"{ind}param {name} {r.i32()} {r.real()} {r.s()}")


def dump_fields(label, ver, r, out, ind):
    f = lambda k, v: out.append(f"{ind}{k} {v}")
    if label == "ScriptGroup":
        f("name s", r.s()); f("active u8", r.u8())
        if ver == 2:
            f("subroutine u8", r.u8())
    elif label == "Script":
        for k in ("name", "comment", "conditionComment", "actionComment"):
            f(k + " s", r.s())
        for k in ("active", "oneShot", "easy", "normal", "hard", "subroutine"):
            f(k + " u8", r.u8())
        if ver >= 2:
            f("delaySeconds i32", r.i32())
    elif label in ("Condition", "ScriptAction", "ScriptActionFalse"):
        f("type i32", r.i32())
        if ver >= (4 if label == "Condition" else 2):
            f("name key", r.key())
        n = r.i32()
        f("params i32", n)
        for _ in range(n):
            dump_param(r, out, ind)
    elif label == "ScriptsPlayers":
        has = r.i32(); f("hasDicts i32", has)
        n = r.i32(); f("count i32", n)
        for _ in range(n):
            f("player s", r.s())
            if has:
                dump_dict(r, out, ind)
    elif label == "ScriptTeams":
        while r.p < len(r.d):
            dump_dict(r, out, ind)


def dump_chunks(d, toc, out, ind):
    p = 0
    while p < len(d):
        cid, ver, size = struct.unpack("<IHi", d[p:p + 10])
        label = toc[cid]
        body = d[p + 10:p + 10 + size]
        out.append(f"{ind}chunk {json.dumps(label)} {ver}")
        r = Reader(body, toc)
        dump_fields(label, ver, r, out, ind + "  ")
        rest = body[r.p:]
        if rest and label in CONTAINERS:
            dump_chunks(rest, toc, out, ind + "  ")
        elif rest:
            out.append(f"{ind}  raw {rest.hex()}")
        p += 10 + size


def dump(data: bytes) -> str:
    assert data[:4] == b"CkMp", "не CkMp"
    n = struct.unpack("<i", data[4:8])[0]
    p, toc, out = 8, {}, ["# scb-text 1"]
    for _ in range(n):
        ln = data[p]; name = data[p + 1:p + 1 + ln].decode("latin1"); cid = struct.unpack("<I", data[p + 1 + ln:p + 5 + ln])[0]
        toc[cid] = name
        out.append(f"toc {cid} {json.dumps(name)}")
        p += 5 + ln
    dump_chunks(data[p:], toc, out, "")
    return "\n".join(out) + "\n"


TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\S+')


def build(text: str) -> bytes:
    toc_list, names = [], {}
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        ind = len(raw) - len(raw.lstrip(" "))
        tok = [json.loads(t) if t.startswith('"') else t for t in TOKEN.findall(raw)]
        if tok[0] == "toc":
            toc_list.append((int(tok[1]), tok[2])); names[tok[2]] = int(tok[1])
        else:
            lines.append((ind, tok))

    def nid(name):
        if name not in names:
            names[name] = max(names.values(), default=0) + 1
            toc_list.append((names[name], name))
        return names[name]

    def real(s):
        return bytes.fromhex(s[2:]) if s.startswith("0x") else struct.pack("<f", float(s))

    def sb(s):
        b = s.encode("latin1"); return struct.pack("<H", len(b)) + b

    def block(i, ind):
        # блок строк с отступом > ind начиная с i; возвращает (байты, следующий i)
        out = bytearray()
        while i < len(lines) and lines[i][0] > ind:
            lind, t = lines[i]
            k = t[0]
            if k == "chunk":
                body, i = block(i + 1, lind)
                out += struct.pack("<IHi", nid(t[1]), int(t[2]), len(body)) + body
                continue
            if k == "dict":
                n = int(t[1]); out += struct.pack("<H", n); i += 1
                for _ in range(n):
                    _, (key, ty, val) = lines[i]; i += 1
                    ti = DICT_TYPES.index(ty)
                    out += struct.pack("<i", (nid(key) << 8) | ti)
                    out += {0: lambda: bytes([int(val)]), 1: lambda: struct.pack("<i", int(val)), 2: lambda: real(val),
                            3: lambda: sb(val), 4: lambda: struct.pack("<H", len(val)) + val.encode("utf-16-le")}[ti]()
                continue
            if k == "param":
                ty = PARAM_TYPES.index(t[1]) if t[1] in PARAM_TYPES else int(t[1])
                out += struct.pack("<i", ty)
                out += b"".join(map(real, t[2:5])) if ty == COORD3D else struct.pack("<i", int(t[2])) + real(t[3]) + sb(t[4])
            elif k == "raw":
                out += bytes.fromhex(t[1])
            else:
                ty = t[1]
                if ty == "s": out += sb(t[2])
                elif ty == "u8": out += bytes([int(t[2])])
                elif ty == "i32":
                    # число параметров считаем сами, чтобы правка строк param не ломала файл
                    n = int(t[2])
                    if k == "params":
                        n = 0
                        while i + 1 + n < len(lines) and lines[i + 1 + n][0] == lind and lines[i + 1 + n][1][0] == "param":
                            n += 1
                    out += struct.pack("<i", n)
                elif ty == "key": out += struct.pack("<i", (nid(t[2]) << 8) | int(t[3]))
                else: raise ValueError(f"неизвестный тип поля: {t}")
            i += 1
        return bytes(out), i

    body, i = block(0, -1)
    assert i == len(lines)
    head = bytearray(b"CkMp" + struct.pack("<i", len(toc_list)))
    for cid, name in toc_list:
        b = name.encode("latin1"); head += bytes([len(b)]) + b + struct.pack("<I", cid)
    return bytes(head) + body


def main(argv):
    cmd, *args = argv
    if cmd == "dump":
        open(args[1], "w").write(dump(open(args[0], "rb").read()))
    elif cmd == "build":
        open(args[1], "wb").write(build(open(args[0]).read()))
    elif cmd == "check":
        ok = True
        for a in args:
            data = open(a, "rb").read()
            same = build(dump(data)) == data
            ok &= same
            print(("OK  " if same else "FAIL"), a, len(data))
        return 0 if ok else 1
    else:
        print(__doc__ or "dump|build|check"); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
