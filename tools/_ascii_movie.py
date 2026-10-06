import sys, json, importlib.util
sys.path.insert(0, '.')
sys.path.insert(0, 'tools')
import tools.arabic as ar
from tools.render_ui import SfnRenderer
import numpy as np

bmap = {int(k): v for k, v in json.load(open('build/fonts/movie_byte_map.json')).items()}
spec = importlib.util.spec_from_file_location('loc_ar', 'translations/loc_ar.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
r = SfnRenderer(open('build/fonts/SUBFNT.SFN', 'rb').read(), 'SUBFNT')
sid = 'LOC_STNMINTR_007'
shaped = ar.process(m.AR[sid])
enc = ''.join(chr(bmap[ord(c)]) if ord(c) in bmap else c for c in shaped)
print("arabic:", m.AR[sid])
print("shaped:", [hex(ord(c)) for c in shaped])
print("bytes :", [hex(ord(c)) for c in enc])
img = r.render(enc)
a = np.array(img)
for y in range(a.shape[0]):
    print("".join("#" if v >= 8 else ("+" if v > 0 else ".") for v in a[y]))
