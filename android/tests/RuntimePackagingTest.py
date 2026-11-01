#!/usr/bin/env python3
"""Small boundary checks for the build-only dependency/ELF packager."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from package_runtime import safe_name, elf_16k, OUT, ROOT, CACHE

for name in ['', '.', '/outside', '../outside', 'a/../../outside', 'a\\outside', 'a\0outside']:
    try: safe_name(name)
    except ValueError: pass
    else: raise AssertionError('Unsafe name accepted: '+repr(name))
assert safe_name('UnityPy/classes/Object.py')=='UnityPy/classes/Object.py'
original=(OUT/'lib/arm64-v8a/libpython3.13.so').read_bytes()
elf_16k(original)
for mode in ['x86', '4k', 'misaligned', 'notelf']:
    bad=bytearray(original)
    if mode=='x86':struct.pack_into('<H',bad,18,62)
    elif mode=='notelf':bad[0]=0
    else:
        start=struct.unpack_from('<Q',bad,32)[0]
        size,count=struct.unpack_from('<HH',bad,54)
        for i in range(count):
            p=start+i*size
            if struct.unpack_from('<I',bad,p)[0]==1:
                if mode=='4k':struct.pack_into('<Q',bad,p+48,4096)
                else:struct.pack_into('<Q',bad,p+16,1)
                break
        else:raise AssertionError('No load segment in fixture')
    try:elf_16k(bad)
    except ValueError:pass
    else:raise AssertionError('Bad ELF accepted: '+mode)
before=hashlib.sha256((OUT/'assets/chaquopy/app.imy').read_bytes()).digest()
with tempfile.TemporaryDirectory(prefix='runtime-pin-test-',dir=CACHE) as directory:
    env=dict(os.environ,ORBEATS_ANDROID_TOOLS=directory)
    command=[sys.executable,str(ROOT/'tools/package_runtime.py')]
    missing=subprocess.run(command,env=env,capture_output=True,text=True)
    assert missing.returncode and 'Missing private prerequisite' in missing.stderr
    entry=json.loads((ROOT/'runtime-lock.json').read_text())[0]
    corrupt=Path(directory)/entry['file'];corrupt.parent.mkdir(parents=True);corrupt.write_bytes(b'tampered dependency')
    modified=subprocess.run(command,env=env,capture_output=True,text=True)
    assert modified.returncode and 'Dependency modified:' in modified.stderr
assert hashlib.sha256((OUT/'assets/chaquopy/app.imy').read_bytes()).digest()==before
print('PASS: runtime packager paths, ARM64/16KiB; wrong ABI/4KiB/misalignment/non-ELF/missing/tampered dependency refusals; failed prerequisites preserve staged assets')
