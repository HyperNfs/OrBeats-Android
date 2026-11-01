#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Offline Android-target Python/UnityPy probe, not an APK or complete converter."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile

project = Path(__file__).resolve().parent
runtime = Path.home()/'.cache/orbeats-android-tools/android-python'
if len(sys.argv) != 2:
    raise SystemExit('Usage: android_writer_check.py PRIVATE_PCM_REPORT_JSON (run check.py first)')
pcm_report = Path(sys.argv[1]).resolve(strict=True)
assert pcm_report.is_relative_to(runtime.parent) and pcm_report.name == 'report.json'
pcm = json.loads(pcm_report.read_text())
upstream = Path.home()/'.cache/beatsaber-mod-research/sources/Wkrotik_OrBeats_android_pipeline'
assert subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() == pcm['upstream_commit']
assert not subprocess.check_output(['git', '-C', str(upstream), 'status', '--porcelain'], text=True).strip()
assert pcm['art']['upstream_bank_matches'] == 10

# The one real loader port is explicit and checked against the original pure wheel.
with zipfile.ZipFile(runtime/'audio-wheels/soundfile-0.13.1-py2.py3-none-any.whl') as wheel:
    original = wheel.read('soundfile.py').decode()
old = "elif _sys.platform == 'linux':\n            _explicit_libname = 'libsndfile.so'"
new = "elif _sys.platform in ('linux', 'android'):\n            _explicit_libname = 'libsndfile.so'"
assert original.count(old) == 1
patched = original.replace(old, new)
assert (runtime/'site/soundfile.py').read_text() == patched
patch = ''.join(difflib.unified_diff(original.splitlines(keepends=True), patched.splitlines(keepends=True),
                                  fromfile='soundfile.py', tofile='soundfile.py'))
assert (project/'patches/soundfile-0.13.1-android.patch').read_text() == patch
for path in [runtime/'native/include/python3.13/Python.h', runtime/'stdlib/encodings/__init__.py',
             runtime/'site/lz4/block/__init__.py', runtime/'site/PIL/Image.py',
             runtime/'unity-source/unitypy-1.20.26/UnityPy/__init__.py']:
    if not path.is_file():
        raise SystemExit('Missing privately staged developer dependency: '+str(path)+'; see README.md')

# Verify the complete extracted source, not just its version string; no codec stubs.
source_archive = runtime/'unitypy-1.20.26.tar.gz'
source_record = json.loads((runtime/'unity-source.json').read_text())
assert hashlib.sha256(source_archive.read_bytes()).hexdigest() == source_record['sha256']
with tarfile.open(source_archive) as archive:
    expected_files = {member.name for member in archive.getmembers() if member.isfile()}
    actual_files = {str(p.relative_to(runtime/'unity-source')) for p in (runtime/'unity-source').rglob('*') if p.is_file()}
    assert actual_files == expected_files, 'Unexpected/missing source files'
    for member in archive.getmembers():
        if member.isfile():
            assert not member.name.startswith('/') and '..' not in Path(member.name).parts
            assert archive.extractfile(member).read() == (runtime/'unity-source'/member.name).read_bytes(), member.name

work = Path(tempfile.mkdtemp(prefix='writer-proof-', dir=runtime.parent))
launcher = work/'android_python'
libraries = runtime/'native/jniLibs/arm64-v8a'
build = ['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I'+str(runtime/'native/include/python3.13'),
         str(project/'tests/android_python.c'), '-L'+str(libraries), '-Wl,-rpath,'+str(libraries),
         '-lpython3.13', '-lm', '-ldl', '-o', str(launcher)]
subprocess.run(build, check=True)
env = dict(os.environ, LD_LIBRARY_PATH=str(runtime/'site/chaquopy/lib')+':'+str(libraries),
           ORBEATS_WRITER_REPORT=str(work/'report.json'), ORBEATS_AUDIO_REPORT=str(work/'audio.json'),
           ORBEATS_PCM_REPORT=str(pcm_report), ORBEATS_UPSTREAM=str(upstream))
env.pop('LD_PRELOAD', None)
command = [str(launcher), str(runtime/'stdlib'), str(runtime/'native/lib-dynload/arm64-v8a'),
           str(runtime/'site'), str(runtime/'unity-source/unitypy-1.20.26')]
assert subprocess.run([str(launcher)], env=env, capture_output=True).returncode == 2
assert subprocess.run(command+[str(work/'missing.py')], env=env, capture_output=True).returncode == 1
assert not (work/'report.json').exists()
subprocess.run(command+[str(project/'tests/android_writer.py')], check=True, env=env)
subprocess.run(command+[str(project/'tests/android_audio.py')], check=True, env=env)
report = json.loads((work/'report.json').read_text())
report['audio'] = json.loads((work/'audio.json').read_text())
report['pcm_art_report'] = str(pcm_report)
report['upstream_commit'] = pcm['upstream_commit']
report['audio_wheels'] = json.loads((runtime/'audio-downloads.json').read_text())
report['soundfile_loader_patch_sha256'] = hashlib.sha256((project/'patches/soundfile-0.13.1-android.patch').read_bytes()).hexdigest()
assert report['platform'] == 'android' and len(report['generated_unityfs_roundtrips']) == 4
assert report['native_pillow_png_512_roundtrip'] and report['native_lz4_brotli_roundtrip']
report['unitypy_source'] = source_record
report['source_unmodified'] = True
report['runtime_downloads'] = json.loads((runtime/'downloads.json').read_text())
report['pure_dependencies'] = json.loads((runtime/'pure-downloads.json').read_text())
report['native_dependencies'] = json.loads((runtime/'native-downloads.json').read_text())
report['pillow_wheels'] = [{'filename': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                           'index': 'https://chaquo.com/pypi-13.1/'}
                          for p in sorted((runtime/'wheels').glob('*.whl'))]
report['compile_command'] = build
report['launcher_error_cases'] = 2
report['launcher_dynamic_dependencies'] = subprocess.check_output(['llvm-readelf', '-d', str(launcher)], text=True)
report['python_dynamic_dependencies'] = subprocess.check_output(['llvm-readelf', '-d', str(libraries/'libpython3.13.so')], text=True)
(work/'report.json').write_text(json.dumps(report, indent=2)+'\n')
print('PASS: unmodified source and missing-argument/script refusals; no APK build or console I/O')
print('REPORT', work/'report.json')
