#!/usr/bin/env python3
"""Offline manual packager for Chaquopy17.2's documented Gradle asset layout.

--fetch explicitly stages pinned public prerequisites privately. No runtime download,
custom JNI or ZIP installer: the app uses the unmodified official AndroidPlatform.
"""
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys
import tempfile
import tarfile
import urllib.request
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get('ORBEATS_ANDROID_TOOLS', str(Path.home()/'.cache/orbeats-android-tools')))
OUT = ROOT/'build/runtime'


def safe_name(name):
    p = PurePosixPath(name)
    if not name or str(p) == '.' or p.is_absolute() or '..' in p.parts or '\\' in name or '\0' in name:
        raise ValueError('Unsafe dependency member: '+name)
    return name


def elf_16k(data):
    if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise ValueError('Expected ARM64 little-endian ELF')
    start = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    loads = 0
    for i in range(count):
        kind, _, offset, address, _, _, _, align = struct.unpack_from('<IIQQQQQQ', data, start+i*size)
        if kind == 1:
            if align < 16384 or offset % align != address % align:
                raise ValueError('Native library is not 16 KiB load-aligned')
            loads += 1
    if not loads:
        raise ValueError('ELF has no load segments')


def write_zip(path, files):
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, 'w', ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            safe_name(name)
            if name.endswith('.so'):
                elf_16k(data)
            info = ZipInfo(name, date_time=(1980, 2, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            z.writestr(info, data)


def main(fetch=False):
    inputs = json.loads((ROOT/'runtime-lock.json').read_text())
    sources = []
    for entry in inputs:
        path = CACHE/safe_name(entry['file'])
        if not path.is_file() and fetch:
            if not entry['url'].startswith('https://'):
                raise ValueError('HTTPS dependency URL required')
            with urllib.request.urlopen(entry['url'], timeout=60) as response:
                data = response.read(64*1024*1024+1)
            if len(data) > 64*1024*1024 or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Dependency hash/size mismatch: '+entry['file'])
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name+'.part')
            tmp.write_bytes(data)
            tmp.replace(path)
        if not path.is_file():
            raise FileNotFoundError('Missing private prerequisite; run python tools/package_runtime.py --fetch: '+str(path))
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Dependency modified: '+entry['file'])
        sources.append((entry, data))
    from build_audio import build as build_audio, NAMES as AUDIO_LIBS
    audio = build_audio(inputs)
    audio_files = {name:(audio/name).read_bytes() for name in AUDIO_LIBS}
    for data in audio_files.values():elf_16k(data)
    if OUT.exists():
        shutil.rmtree(OUT)
    assets = OUT/'assets/chaquopy'
    libs = OUT/'lib/arm64-v8a'
    assets.mkdir(parents=True)
    libs.mkdir(parents=True)
    abi = 'arm64-v8a'
    requirements = {'chaquopy/lib/'+name:data for name,data in audio_files.items()}
    app = {str(p.relative_to(ROOT/'python')):p.read_bytes() for p in (ROOT/'python').rglob('*.py') if '__pycache__' not in p.parts}
    app['writer_probe.py'] = (ROOT/'development/conversion/tests/android_writer.py').read_bytes()
    stdnative = {}
    bootstrap = {}
    notices = ['OrBeats Android: GPL-3.0-only. No game assets are included.\n'
               'Chaquopy17.2.0 / CPython3.13.16 / UnityPy1.20.26.\n'
               'SQLite3 is public domain: https://sqlite.org/copyright.html\n'
               'Pillow core PNG/JPEG only; optional FreeType font backend is omitted.\n'
               'This software is based in part on the work of the Independent JPEG Group.\n'
               'Bootstrap pkg_resources vendors packaging/platformdirs/typing_extensions/'
               'importlib_resources/zipp/more_itertools and Jason R. Coombs\' MIT-licensed '
               'jaraco text/context/functools; original notices follow.\n'
               'CPython, bootstrap and dependency source locations and hashes follow.\n']
    for entry, data in sources:
        kind = entry['kind']
        name = Path(entry['file']).name
        notices.append('\n=== '+name+' ===\nSource: '+entry['url']+'\nSHA256: '+entry['sha256']+'\n')
        if kind == 'java':
            (OUT/'chaquopy_java.jar').write_bytes(data)
        elif kind == 'bootstrap':
            (assets/'bootstrap.imy').write_bytes(data)
        elif kind == 'jni':
            elf_16k(data)
            (libs/'libchaquopy_java.so').write_bytes(data)
        elif kind == 'module':
            bootstrap['java/chaquopy.so'] = data
        elif kind == 'stdlib':
            (assets/'stdlib-common.imy').write_bytes(data)
        elif kind == 'cacert':
            (assets/'cacert.pem').write_bytes(data)
        elif kind == 'license':
            text = data.decode('utf-8')
            if name.endswith('-SOURCE.txt'):
                text = text.split('*/', 1)[0]+'*/\n'
            notices.append(text)
        elif kind == 'target':
            patterns = ['_bz2.*', '_ctypes.*', '_datetime.*', '_lzma.*', '_random.*',
                        '_opcode.*', '_struct.*', 'binascii.*', 'math.*', 'mmap.*', 'zlib.*']
            with ZipFile(io.BytesIO(data)) as z:
                for member in z.namelist():
                    if member.endswith('/'):
                        continue
                    safe_name(member)
                    content = z.read(member)
                    if member.startswith('jniLibs/'+abi+'/'):
                        basename = member.removeprefix('jniLibs/'+abi+'/')
                        assert '/' not in basename
                        elf_16k(content)
                        (libs/basename).write_bytes(content)
                    elif member.startswith('lib-dynload/'+abi+'/'):
                        basename = member.removeprefix('lib-dynload/'+abi+'/')
                        (bootstrap if any(fnmatch.fnmatch(basename, x) for x in patterns) else stdnative)[basename] = content
        elif kind == 'audio-source':
            found = False
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
                for member in archive.getmembers():
                    p = PurePosixPath(safe_name(member.name))
                    if member.isfile() and len(p.parts)==2 and (p.name.startswith(('COPYING','LICENSE')) or p.name=='AUTHORS'):
                        if entry['name']=='flac' and p.name not in ('COPYING.Xiph','AUTHORS'):continue
                        notices.append('\n--- '+p.name+' ---\n'+archive.extractfile(member).read().decode('utf-8'));found=True
            if not found:raise ValueError('Missing native source license: '+entry['name'])
        elif kind == 'orbeats':
            modules = {'additive_library', 'additive_modes', 'additive_presentation', 'additive_lighting',
                       'native_hash', 'prepare_additive_media', 'import_v4_additive', 'additive_v4_native',
                       'import_v3_additive', 'additive_v3_native', 'import_v2_additive',
                       'prepare_additive_bundle', 'vorbis_audio', 'hevag_encoder',
                       'additive_companion', 'console_transaction', 'score_source',
                       'goldhen_config', 'library_manager', 'extras_manager', 'release_updates'}
            found = set()
            with ZipFile(io.BytesIO(data)) as z:
                for member in z.namelist():
                    p = PurePosixPath(safe_name(member))
                    if p.name == 'LICENSE' and len(p.parts) == 2:
                        notices.append(z.read(member).decode('utf-8'))
                    if p.stem in modules and p.suffix == '.py' and ('tools' in p.parts or 'scripts' in p.parts or 'webapp' in p.parts):
                        if p.stem in found: raise ValueError('Duplicate OrBeats module: '+p.stem)
                        relative = str(p).split('/orbeats/', 1)[1]
                        app['orbeats_pipeline/'+relative] = z.read(member); found.add(p.stem)
                for relative in ('tools/native/fnv.c','src/main.cpp'):
                    matches=[n for n in z.namelist() if n.endswith('/orbeats/'+relative)]
                    if len(matches)!=1:raise ValueError('Missing pinned OrBeats source: '+relative)
                    app['orbeats_pipeline/'+relative]=z.read(matches[0])
            with tempfile.TemporaryDirectory(prefix='orbeats-hash-',dir=CACHE) as work:
                source=Path(work)/'fnv.c';target=Path(work)/'orbeats_hash.so'
                source.write_bytes(app['orbeats_pipeline/tools/native/fnv.c'])
                subprocess.run(['clang','--target=aarch64-linux-android26','-fno-termux-rpath','-O3','-fPIC','-shared','-fstack-protector-strong',
                    '-Wl,-z,max-page-size=16384','-Wl,-z,relro,-z,now','-Wl,-soname,orbeats_hash.so',str(source),'-o',str(target)],check=True)
                content=target.read_bytes();elf_16k(content)
                app['orbeats_pipeline/tools/native/orbeats_hash.so']=content
            if found != modules: raise ValueError('Missing pinned OrBeats preparation/management modules')
            app['orbeats_pipeline/__init__.py'] = b''
        elif kind == 'vendor-license-wheel':
            with ZipFile(io.BytesIO(data)) as z:
                found = False
                for member in z.namelist():
                    if 'LICENSE' in member.upper() or 'COPYING' in member.upper():
                        notices.append('\n--- '+member+' ---\n'+z.read(member).decode('utf-8'))
                        found = True
                if not found:
                    raise ValueError('Missing vendored dependency license: '+entry['file'])
        elif kind == 'wheel':
            with ZipFile(io.BytesIO(data)) as z:
                for member in z.namelist():
                    # shortcut: PNG/JPEG check needs no fonts; add a 16KiB-aligned FreeType before font work.
                    if member.endswith('/') or member.endswith('/RECORD') or member == 'PIL/_imagingft.so':
                        continue
                    safe_name(member)
                    content = z.read(member)
                    if member in requirements and requirements[member] != content:
                        raise ValueError('Conflicting dependency member: '+member)
                    requirements[member] = content
                    if 'LICENSE' in member.upper() or 'COPYING' in member.upper():
                        notices.append('\n--- '+member+' ---\n'+content.decode('utf-8'))
        elif kind == 'fsb5':
            found=set()
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
                for member in archive.getmembers():
                    name=safe_name(member.name).removeprefix('fsb5-1.0/')
                    if member.isfile() and name.startswith('fsb5/') and name.endswith('.py'):
                        requirements[name]=archive.extractfile(member).read();found.add(name)
            if len(found)!=5:raise ValueError('Pinned fsb5 source layout changed')
        elif kind == 'unity':
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
                for member in archive.getmembers():
                    name = safe_name(member.name).removeprefix('unitypy-1.20.26/')
                    if member.isfile() and (name.startswith('UnityPy/') or name == 'LICENSE'):
                        content = archive.extractfile(member).read()
                        if name == 'LICENSE':
                            notices.append(content.decode('utf-8'))
                        # Optional desktop FMOD SDK binaries are proprietary, not APK dependencies.
                        elif not name.endswith('.pyc') and not name.startswith('UnityPy/lib/FMOD/'):
                            requirements[name] = content
        else:
            raise ValueError('Unknown dependency kind: '+kind)
    # SoundFile's Linux SONAME fallback also applies to Android's real libsndfile.
    old = b"elif _sys.platform == 'linux':\n            _explicit_libname = 'libsndfile.so'"
    if requirements['soundfile.py'].count(old) != 1: raise ValueError('SoundFile patch drift')
    requirements['soundfile.py'] = requirements['soundfile.py'].replace(old, b"elif _sys.platform in ('linux', 'android'):\n            _explicit_libname = 'libsndfile.so'")
    notices.append('\nSoundFile0.13.1 Android patch: Linux libsndfile.so fallback also accepts sys.platform android. Original sources otherwise unchanged.\n')
    old = b"    def __getattr__(self, item: str):\n        if hasattr(self.reader, item):\n            return getattr(self.reader, item)"
    new = b"    def __getattr__(self, item: str):\n        reader = self.__dict__.get('reader')\n        if reader is None:\n            raise AttributeError(item)\n        return getattr(reader, item)"
    member = 'UnityPy/files/ObjectReader.py'
    if requirements[member].count(old) != 1: raise ValueError('UnityPy copy compatibility patch drift')
    requirements[member] = requirements[member].replace(old, new)
    notices.append('\nUnityPy1.20.26 ObjectReader patch: guard absent reader during copy.copy reconstruction and raise AttributeError for missing attributes. All other Python sources unchanged.\n')
    notices.append('\nNative audio built locally for Android26/ARM64/16KiB, no Termux RPATH: Ogg1.3.6, Vorbis1.3.7, FLAC1.5.0, Opus1.5.2, libsndfile1.2.2. Original C sources and SHA256 pins above; no FLAC executables/C++ bindings.\n')
    assert 'UnityPy/__init__.py' in requirements and 'PIL/Image.py' in requirements
    write_zip(assets/'requirements-common.imy', {})
    write_zip(assets/('requirements-'+abi+'.imy'), requirements)
    write_zip(assets/('stdlib-'+abi+'.imy'), stdnative)
    for name, data in bootstrap.items():
        elf_16k(data)
        dest = assets/'bootstrap-native'/abi/safe_name(name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    write_zip(assets/'app.imy', app)
    # SHA1 is upstream's cache-invalidation format, not our integrity/signature boundary.
    build = {'python_version': '3.13', 'extract_packages': ['orbeats_pipeline'], 'assets': {
        str(f.relative_to(assets)): hashlib.sha1(f.read_bytes()).hexdigest()
        for f in sorted(assets.rglob('*')) if f.is_file()}}
    (assets/'build.json').write_text(json.dumps(build, sort_keys=True, indent=2)+'\n')
    (OUT/'assets/NOTICES.txt').write_text('\n'.join(notices)+'\n\n'+(ROOT/'LICENSE').read_text())
    print('PASS: pinned official Chaquopy assets/JNI + explicit SoundFile/UnityPy compatibility patches; all ELF16KiB aligned')


if __name__ == '__main__':
    if sys.argv[1:] not in [[], ['--fetch']]:
        raise SystemExit('Usage: package_runtime.py [--fetch]')
    main(fetch=sys.argv[1:] == ['--fetch'])
