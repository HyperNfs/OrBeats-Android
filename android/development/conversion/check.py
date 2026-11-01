#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Offline developer proof. No app build, network, game assets, or console I/O."""
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import wave
import zipfile

project = Path(__file__).resolve().parent
home = Path.home()
tools = home / '.cache/orbeats-android-tools'
upstream = home / '.cache/beatsaber-mod-research/sources/Wkrotik_OrBeats_android_pipeline'
site = tools / 'conversion-reference'
prefix = tools / 'root/data/data/com.termux/files/usr'
java = prefix / 'lib/jvm/java-21-openjdk/bin/java'
javac = java.with_name('javac')
commit = '098897736e089107704ec1633daff8922087fcc8'
assert subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() == commit
assert not subprocess.check_output(['git', '-C', str(upstream), 'status', '--porcelain'], text=True).strip()
art = Path('/apex/com.android.art/bin/dalvikvm')
if not art.is_file(): art = Path('/system/bin/dalvikvm')
boot_classpath = os.environ.get('BOOTCLASSPATH')
if not boot_classpath:
    raise SystemExit('Missing Android BOOTCLASSPATH; run this developer check on the phone')
for required in [java, javac, tools/'r8.jar', tools/'android.jar', site/'packages.json', art]:
    if not required.is_file():
        raise SystemExit('Missing developer prerequisite: ' + str(required) + '; see README.md')
work = Path(tempfile.mkdtemp(prefix='pcm-proof-', dir=tools))
for name in ['classes', 'dex', 'input', 'reference', 'java', 'invalid', 'art', 'art-data/dalvik-cache']:
    (work/name).mkdir(parents=True)
env = dict(os.environ, LD_LIBRARY_PATH=str(prefix/'lib') + ':' + os.environ.get('PREFIX', '') + '/lib')
def run(*args):
    subprocess.run([str(arg) for arg in args], check=True, env=env)
source = project/'src/dev/orbeats/conversion/Pcm16Fsb.java'
run(javac, '--release', '8', '-Xlint:all,-options,-strictfp', '-Werror', '-d', work/'classes',
    source, project/'tests/Pcm16FsbTest.java')
run(java, '-cp', work/'classes', 'dev.orbeats.conversion.Pcm16FsbTest')

# Generated audio only: channel order, all 16-bit values, clipping threshold,
# float32 rounding and a conventional odd-sized metadata chunk.
cases = {
    'silence': [(0, 0)] * 44100,
    'quiet': [(1, -1), (2, -2), (1000, -1000)] * 14700,
    'below_threshold': [(32440, -32440)] * 44100,
    'above_threshold': [(32441, -32441)] * 44100,
    'extremes': [(-32768, 32767)] * 44100,
    'all_int16': [(i - 32768, 32767 - i) for i in range(65536)],
    'stereo_tone': [(int(math.sin(i * 2 * math.pi * 440 / 44100) * 21000),
                     int(math.sin(i * 2 * math.pi * 660 / 44100) * 17000)) for i in range(132300)],
}
for name, frames in cases.items():
    data = array('h', (s for pair in frames for s in pair))
    if sys.byteorder != 'little': data.byteswap()
    with wave.open(str(work/'input'/f'{name}.wav'), 'wb') as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(44100)
        wav.writeframes(data.tobytes())
del cases, data, frames
raw = (work/'input/quiet.wav').read_bytes()
metadata = raw[:12] + b'JUNK' + struct.pack('<I', 3) + b'abc\0' + raw[12:]
metadata = metadata[:4] + struct.pack('<I', len(metadata)-8) + metadata[8:]
(work/'input/odd_metadata.wav').write_bytes(metadata)
fmt18 = raw[:16] + struct.pack('<I', 18) + raw[20:36] + b'\0\0' + raw[36:]
trailing = raw + b'JUNK' + struct.pack('<I', 0)
for name, contents in [('fmt18', fmt18), ('trailing_metadata', trailing)]:
    (work/'input'/f'{name}.wav').write_bytes(contents[:4]+struct.pack('<I', len(contents)-8)+contents[8:])
run('proot-distro', 'login', 'debian', '--bind', str(upstream)+':/upstream',
    '--bind', str(site)+':/ref', '--bind', str(work)+':/work', '--bind', str(project)+':/proof',
    '--', 'env', 'PYTHONPATH=/ref/site', 'PYTHONDONTWRITEBYTECODE=1', 'python3', '/proof/tests/reference.py')
results = []
for wav in sorted((work/'input').glob('*.wav')):
    bank = work/'java'/(wav.stem+'.fsb')
    run(java, '-cp', work/'classes', 'dev.orbeats.conversion.Pcm16FsbTest', wav, bank)
    actual = bank.read_bytes()
    expected = (work/'reference'/bank.name).read_bytes()
    if actual != expected:
        offset = next((i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]), min(len(actual), len(expected)))
        raise AssertionError(f'{wav.name}: upstream mismatch at byte {offset}')
    with wave.open(str(wav)) as w: frames = w.getnframes()
    assert actual[:4] == b'FSB5' and len(actual) == 125 + frames*4
    assert struct.unpack_from('<Q', actual, 60)[0] >> 34 == frames
    assert struct.unpack_from('<I', actual, 20)[0] == frames*4
    results.append({'fixture': wav.name, 'frames': frames, 'bank_bytes': len(actual),
                    'sha256': hashlib.sha256(actual).hexdigest()})
    print('PASS: byte-identical upstream bank:', wav.name, flush=True)
# RIFF ambiguity and scan-budget failures must not leave new output files.
for name, contents in [
    ('duplicate_format', raw[:36]+raw[12:36]+raw[36:]),
    ('duplicate_data', raw+raw[36:]),
    ('excessive_chunks', raw[:12]+(b'JUNK'+struct.pack('<I', 0))*257+raw[12:]),
]:
    bad = work/'invalid'/f'{name}.wav'; out = bad.with_suffix('.fsb')
    bad.write_bytes(contents[:4]+struct.pack('<I', len(contents)-8)+contents[8:])
    process = subprocess.run([str(java), '-cp', str(work/'classes'), 'dev.orbeats.conversion.Pcm16FsbTest', str(bad), str(out)],
                             env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert process.returncode != 0 and 'java.io.IOException:' in process.stderr and not out.exists(), name
    print('PASS: refused', name, flush=True)

# Exercise the maximum accepted duration without keeping a full song in heap.
stress_in = work/'maximum.wav'; stress_out = work/'maximum.fsb'
max_frames = 600*44100; pcm_bytes = max_frames*4
header = bytearray(raw[:44]); struct.pack_into('<I', header, 4, pcm_bytes+36)
struct.pack_into('<I', header, 40, pcm_bytes)
try:
    with stress_in.open('wb') as f:
        f.write(header); f.truncate(44+pcm_bytes)
    run(java, '-Xmx16m', '-cp', work/'classes', 'dev.orbeats.conversion.Pcm16FsbTest', stress_in, stress_out)
    assert stress_out.stat().st_size == 125+pcm_bytes
    with stress_out.open('rb') as f:
        assert struct.unpack_from('<Q', f.read(125), 60)[0] >> 34 == max_frames
    stress_out.unlink()
    # One frame over the limit must fail before scanning a large payload.
    pcm_bytes += 4
    struct.pack_into('<I', header, 4, pcm_bytes+36); struct.pack_into('<I', header, 40, pcm_bytes)
    with stress_in.open('wb') as f:
        f.write(header); f.truncate(44+pcm_bytes)
    p = subprocess.run([str(java), '-Xmx16m', '-cp', str(work/'classes'), 'dev.orbeats.conversion.Pcm16FsbTest', str(stress_in), str(stress_out)],
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert p.returncode != 0 and '1..600 seconds' in p.stderr and not stress_out.exists()
finally:
    stress_in.unlink(missing_ok=True); stress_out.unlink(missing_ok=True)
print('PASS: 600-second conversion under 16 MiB Java heap; 600 seconds + one frame refused', flush=True)
run(java, '-cp', tools/'r8.jar', 'com.android.tools.r8.D8', '--min-api', '26',
    '--lib', tools/'android.jar', '--output', work/'dex', *sorted((work/'classes').rglob('*.class')))
dex = (work/'dex/classes.dex').read_bytes()
assert dex.startswith(b'dex\n') and b'Ldev/orbeats/conversion/Pcm16Fsb;' in dex
# This changes only this new process's class path, not the device boot configuration.
jar = work/'dex/proof.jar'
with zipfile.ZipFile(jar, 'w') as archive:
    archive.write(work/'dex/classes.dex', 'classes.dex')
art_env = dict(env, ANDROID_DATA=str(work/'art-data'))
for variable in ['LD_LIBRARY_PATH', 'LD_PRELOAD']:
    art_env.pop(variable, None)
art_command = [str(art), '-Xnoimage-dex2oat', '-Djava.io.tmpdir='+str(work),
               '-Xbootclasspath:'+boot_classpath+':'+str(jar), 'dev.orbeats.conversion.Pcm16FsbTest']
subprocess.run(art_command, check=True, env=art_env)
for case in results:
    bank = work/'art'/(Path(case['fixture']).stem+'.fsb')
    subprocess.run(art_command+[str(work/'input'/case['fixture']), str(bank)], check=True, env=art_env)
    assert hashlib.sha256(bank.read_bytes()).hexdigest() == case['sha256'], case['fixture']
    print('PASS: Android ART byte-identical upstream bank:', case['fixture'], flush=True)
android_api = subprocess.check_output(['/system/bin/getprop', 'ro.build.version.sdk'], text=True).strip()
assert android_api.isdigit()
assert not subprocess.check_output(['git', '-C', str(upstream), 'status', '--porcelain'], text=True).strip()
report = {'upstream_commit': commit, 'java_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'cases': results, 'reference': json.loads((work/'reference.json').read_text()),
          'reference_packages': json.loads((site/'packages.json').read_text()),
          'dex_bytes': len(dex), 'dex_sha256': hashlib.sha256(dex).hexdigest(),
          'stress': {'seconds': 600, 'frames': max_frames, 'java_max_heap_mib': 16, 'oversized_refused': True},
          'ambiguous_riff_cases_refused': 3,
          'art': {'binary': str(art), 'android_api': int(android_api), 'unit_checks': 31,
                  'upstream_bank_matches': len(results), 'installed_apk': False},
          'not_tested': ['Activity/APK integration', 'OGG decoding/resampling', 'Unity bundle writing', 'PS4 playback']}
(work/'report.json').write_text(json.dumps(report, indent=2)+'\n')
print('PASS: API26 DEX compilation and standalone Android ART execution (NOT installed APK/Activity)', flush=True)
print('REPORT', work/'report.json', flush=True)
