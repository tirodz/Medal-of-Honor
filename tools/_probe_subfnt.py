import sys, glob
sys.path.insert(0, '.')
sys.path.insert(0, 'tools')
from tools.loc import Loc
from tools.sfn import SfnFont

# all bytes >=0x80 used across every language block of every movie LOC
used = set()
for f in sorted(glob.glob('extracted/MOH4/DATA/SHARED/MOVIES/LOC/*.LOC')):
    loc = Loc(open(f, 'rb').read())
    for b in loc.blocks:
        for s in b['strings']:
            for c in s:
                if ord(c) >= 0x80:
                    used.add(ord(c))
print("distinct bytes>=0x80 in all LOC blocks:", len(used), sorted(hex(u) for u in used))

for name in ['SUBFNT.SFN', 'OBJFONT.SFN', 'TPRO12.SFN', 'DBFNT.SFN']:
    fo = SfnFont.parse('extracted/MOH4/DATA/' + name)
    codes = {c.code for c in fo.chars}
    covered = {u for u in used if u in codes}
    print(f"{name}: covers {len(covered)}/{len(used)} of LOC high bytes; missing={sorted(hex(u) for u in used-covered)}")
