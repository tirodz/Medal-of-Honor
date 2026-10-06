import sys, glob, re
sys.path.insert(0, '.')
sys.path.insert(0, 'tools')
from tools.loc import Loc
mx = 0
for f in sorted(glob.glob('extracted/MOH4/DATA/SHARED/MOVIES/LOC/*.LOC')):
    loc = Loc(open(f, 'rb').read())
    for s in loc.blocks[0]['strings']:
        for c in s:
            mx = max(mx, ord(c))
print("max byte in English LOC blocks:", hex(mx))
loc = Loc(open('extracted/MOH4/DATA/SHARED/MOVIES/LOC/STNMINTR.LOC', 'rb').read())
for i, b in enumerate(loc.blocks):
    hi = sum(1 for s in b['strings'] for c in s if ord(c) >= 0x80)
    print(f"  block{i}: bytes>=0x80 = {hi}")
d = open('extracted/MOH4/MOH4RDVD.ELF', 'rb').read()
for m in re.finditer(rb'[\x20-\x7e]{3,}', d):
    s = m.group()
    if b'sub' in s.lower() and b'font' in s.lower():
        print('  font-name:', s.decode())
