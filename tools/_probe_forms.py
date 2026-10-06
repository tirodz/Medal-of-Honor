import sys, os, glob, json, importlib.util
sys.path.insert(0, '.')
sys.path.insert(0, 'tools')
import tools.arabic as ar

rows = json.load(open('translations/loc_strings.json'))
spec = importlib.util.spec_from_file_location('loc_ar', 'translations/loc_ar.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
AR = m.AR

forms = set()
missing = []
for r in rows:
    sid = r['id']
    if sid not in AR:
        missing.append(sid); continue
    shaped = ar.process(AR[sid])
    for ch in shaped:
        o = ord(ch)
        if 0xFE70 <= o <= 0xFEFF or 0x0600 <= o <= 0x06FF:
            forms.add(o)
print("strings:", len(rows), "translated:", len(AR), "missing:", missing)
print("distinct presentation forms needed:", len(forms))
print("forms:", sorted(hex(f) for f in forms))
extra = set()
for r in rows:
    if r['id'] not in AR: continue
    for ch in ar.process(AR[r['id']]):
        o = ord(ch)
        if not (0xFE70 <= o <= 0xFEFF or 0x0600 <= o <= 0x06FF):
            extra.add(ch)
print("non-arabic chars used:", sorted(repr(c) for c in extra))
