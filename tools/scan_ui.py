import glob, os, collections, sys
toks = [b'Mission', b'Objective', b'Options', b'Settings', b'Resume', b'Quit',
        b'Weapon', b'Ammo', b'Health', b'Score', b'Victory', b'Defeat',
        b'Paused', b'Difficulty', b'Press']
exts = {'.STR', '.LOC', '.XML', '.REZ', '.CFG', '.CNF', '.TDB', '.TXT',
        '.MPC', '.SSH', '.STF', '.CNF'}
byext = collections.Counter(); samples = {}
for p in glob.glob('extracted/**/*', recursive=True):
    if not os.path.isfile(p):
        continue
    e = os.path.splitext(p)[1].upper()
    if e not in exts:
        continue
    try:
        raw = open(p, 'rb').read()
    except Exception:
        continue
    hit = any(t in raw or t.lower() in raw for t in toks)
    if not hit:
        u16 = any(b'\x00'.join(t[i:i + 1] for i in range(len(t))) in raw for t in toks)
        hit = u16
    if hit:
        byext[e] += 1
        samples.setdefault(e, p)
print("non-STRINGS files with UI-ish English:", dict(byext))
for e, p in sorted(samples.items()):
    print(f"  {e}: {p}")

