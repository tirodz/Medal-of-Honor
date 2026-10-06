import sys, glob, re
sys.path.insert(0, '.')
sys.path.insert(0, 'tools')
from tools.viv import Viv

# 1. LOADING.VIV header
raw = open('extracted/MOH4/DATA/1/1_1/LOADING.VIV', 'rb').read()
print("LOADING.VIV size", len(raw), "head", raw[:48])

# 2. MOHFE.VIV contents
v = Viv.parse('extracted/MOH4/DATA/SHARED/UI/FE/MOHFE.VIV')
print("MOHFE.VIV entries:", len(v.entries))
for e in v.entries[:40]:
    print("   ", e.name, len(e.data))

# 3. grep UI xml for font names
for p in glob.glob('extracted/MOH4/DATA/SHARED/UI/**/*', recursive=True):
    if p.lower().endswith(('.xml', '.cfg', '.txt')):
        t = open(p, 'rb').read()
        if b'font' in t.lower() or b'Font' in t:
            print("FONT REF in", p)
            for m in re.finditer(rb'[\x20-\x7e]{3,}', t):
                s = m.group()
                if b'font' in s.lower():
                    print("     ", s.decode()[:70])
