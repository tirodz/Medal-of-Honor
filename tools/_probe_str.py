import sys, glob, re, struct
sys.path.insert(0, '.')
sys.path.insert(0, 'tools')

f = 'extracted/MOH4/DATA/1/1_1/LEVEL_A.STR'
d = open(f, 'rb').read()
print("size", len(d), "head", d[:32])
# find all FntS offsets and parse minimal header
for m in re.finditer(rb'FntS', d):
    o = m.start()
    total, ver, nchar, flags = struct.unpack_from('<IHHI', d, o + 4)
    cx, cy, asc, desc = struct.unpack_from('<BBBB', d, o + 16)
    cio, ko, so = struct.unpack_from('<III', d, o + 20)
    print(f"  FntS@{hex(o)} total={total} ver={ver} nchar={nchar} flags=0x{flags:08x} "
          f"asc={asc} desc={desc} cio={cio} ko={ko} so={so}")
