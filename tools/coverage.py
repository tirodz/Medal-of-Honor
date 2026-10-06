"""Report untranslated strings per table and dump the multiplayer set."""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from tools.viv import Viv  # noqa: E402
from tools.inject_strings import _unescape  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tr = json.load(open(os.path.join(HERE, "translations", "ar_final.json")))

paths = ["extracted/MOH4/DATA/SHARED/STRINGMP.VIV"]
paths += sorted(__import__("glob").glob(
    os.path.join(HERE, "extracted", "**", "STRINGS.VIV"), recursive=True))

all_missing = {}
for p in paths:
    v = Viv.parse(p)
    t = v.entries[0].data.decode("utf-16-le")
    ids = [m.group(1) for m in re.finditer(r'name="([^"]+)"', t)]
    miss = [i for i in ids if i not in tr and _unescape(i) not in tr]
    print(f"{os.path.relpath(p, HERE):48s} ids={len(ids):4d} missing={len(miss):4d}")
    for m in re.finditer(r'<(local|global)string name="([^"]+)">(.*?)</\1string>', t, re.DOTALL):
        sid = m.group(2)
        if sid in tr or _unescape(sid) in tr:
            continue
        e = re.search(r'<english value="(.*?)"\s*/>', m.group(3), re.DOTALL)
        all_missing.setdefault(sid, e.group(1) if e else "")

json.dump(all_missing, open(os.path.join(HERE, "translations", "untranslated.json"), "w"),
          ensure_ascii=False, indent=1)
print("\ntotal untranslated unique ids:", len(all_missing))
