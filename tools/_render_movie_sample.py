import sys, json, importlib.util
sys.path.insert(0, '.')
sys.path.insert(0, 'tools')
import tools.arabic as ar
from tools.render_ui import SfnRenderer
from PIL import Image

bmap = {int(k): v for k, v in json.load(open('build/fonts/movie_byte_map.json')).items()}
spec = importlib.util.spec_from_file_location('loc_ar', 'translations/loc_ar.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
r = SfnRenderer(open('build/fonts/SUBFNT.SFN', 'rb').read(), 'SUBFNT')
samples = ['LOC_STNMINTR_007', 'LOC_STNMINTR_021', 'LOC_GAMEOUTR_005',
           'LOC_BOBCINTR_021', 'LOC_NAFCINTR_033', 'LOC_STNMINTR_037']
imgs = []
for sid in samples:
    shaped = ar.process(m.AR[sid])
    enc = ''.join(chr(bmap[ord(c)]) if ord(c) in bmap else c for c in shaped)
    imgs.append(r.render(enc))
W = max(i.width for i in imgs) + 8
H = sum(i.height + 6 for i in imgs)
sheet = Image.new('L', (W, H), 0)
y = 0
for i in imgs:
    sheet.paste(i, (4, y)); y += i.height + 6
sheet.save('build/movies/_verify_sample.png')
print("saved", sheet.size)
