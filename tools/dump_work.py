import json
e = json.load(open('translations/strings.json'))
g = [x for x in e if x['kind'] == 'global']
open('translations/_work_global.txt', 'w').write(''.join(f"{x['id']}\t{x['english']}\n" for x in g))
ui = [x for x in e if '/1_99/' in x['source'] and not x['id'].startswith('CREDIT')]
open('translations/_work_ui.txt', 'w').write(''.join(f"{x['id']}\t{x['english']}\n" for x in ui))
mi = [x for x in e if x['kind'] == 'local' and '/1_99/' not in x['source']]
open('translations/_work_mission.txt', 'w').write(''.join(f"{x['id']}\t{x['source'].split('/')[-2]}\t{x['english']}\n" for x in mi))
print("global", len(g), "ui", len(ui), "mission", len(mi))
