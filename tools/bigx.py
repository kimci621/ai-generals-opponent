# Извлекает файлы из архива .big (формат BIGF) по подстроке имени
import struct, sys, os
src, out, *pats = sys.argv[1:]
d = open(src, 'rb').read()
assert d[:4] in (b'BIGF', b'BIG4'), d[:4]
n = struct.unpack('>I', d[8:12])[0]; p = 16
for _ in range(n):
    off, size = struct.unpack('>II', d[p:p+8]); p += 8
    e = d.index(b'\0', p); name = d[p:e].decode('latin1'); p = e + 1
    if any(s.lower() in name.lower() for s in pats):
        print(name, size)
        dst = os.path.join(out, name.replace('\\', '/')); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(d[off:off+size])
