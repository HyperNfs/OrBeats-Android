"""Build pinned modern Xiph/libsndfile decoders privately on this ARM64 phone.

The old wheel decoder releases are not used on downloaded maps. No global
installation, NDK/Gradle switch, executable decoder or source patch is needed.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[1]
CACHE=Path(os.environ.get('ORBEATS_ANDROID_TOOLS',Path.home()/'.cache/orbeats-android-tools'))
NAMES=('libogg.so','libvorbis.so','libvorbisenc.so','libvorbisfile.so','libFLAC.so','libopus.so','libsndfile.so')


def build(entries):
    sources=[e for e in entries if e['kind']=='audio-source']
    if [e['name'] for e in sources]!=['ogg','vorbis','flac','opus','sndfile']:
        raise ValueError('Unexpected native audio source set/order')
    for e in sources:
        if hashlib.sha256((CACHE/e['file']).read_bytes()).hexdigest()!=e['sha256']:
            raise ValueError('Native audio source changed: '+e['file'])
    compiler=subprocess.check_output(['clang','--version'],text=True)
    recipe=Path(__file__).read_bytes()+json.dumps(sources,sort_keys=True).encode()+compiler.encode()
    key=hashlib.sha256(recipe).hexdigest()[:24]
    target=CACHE/'audio-modern'/('native-'+key)
    if (target/'build.json').is_file():
        report=json.loads((target/'build.json').read_text())
        for name,sha in report['files'].items():
            if name not in NAMES or hashlib.sha256((target/name).read_bytes()).hexdigest()!=sha:
                raise ValueError('Built native audio changed; remove only this private cache: '+str(target))
        if set(report['files'])!=set(NAMES):raise ValueError('Incomplete native audio cache')
        return target
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='building-',dir=target.parent) as directory:
        work=Path(directory);prefix=work/'prefix'
        env=dict(os.environ,PKG_CONFIG_LIBDIR=str(prefix/'lib/pkgconfig'),PKG_CONFIG_PATH=str(prefix/'lib/pkgconfig'))
        env['LD_LIBRARY_PATH']=str(prefix/'lib')+':'+env.get('LD_LIBRARY_PATH','')
        for e in sources:
            source=work/e['name'];source.mkdir()
            with tarfile.open(CACHE/e['file']) as archive:archive.extractall(source,filter='data')
            source=next(p for p in source.iterdir() if p.is_dir())
            output=work/('build-'+e['name'])
            flags=['cmake','-S',str(source),'-B',str(output),'-G','Ninja',
                '-DCMAKE_POLICY_VERSION_MINIMUM=3.5','-DCMAKE_BUILD_TYPE=Release',
                '-DCMAKE_C_COMPILER=clang','-DCMAKE_CXX_COMPILER=clang++',
                '-DCMAKE_C_FLAGS=--target=aarch64-linux-android26 -fno-termux-rpath -fstack-protector-strong',
                '-DCMAKE_CXX_FLAGS=--target=aarch64-linux-android26 -fno-termux-rpath -fstack-protector-strong',
                '-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384 -Wl,-z,relro,-z,now -Wl,--pack-dyn-relocs=android',
                '-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON','-DCMAKE_INSTALL_PREFIX='+str(prefix),
                '-DCMAKE_INSTALL_LIBDIR=lib','-DCMAKE_PREFIX_PATH='+str(prefix),
                '-DCMAKE_INSTALL_RPATH=','-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON',
                '-DBUILD_SHARED_LIBS=ON','-DBUILD_TESTING=OFF','-DBUILD_EXAMPLES=OFF',
                '-DBUILD_PROGRAMS=OFF','-DBUILD_CXXLIBS=OFF','-DBUILD_DOCS=OFF',
                '-DINSTALL_MANPAGES=OFF','-DENABLE_CPACK=OFF','-DENABLE_MPEG=OFF',
                '-DENABLE_MULTITHREADING=OFF','-DOPUS_BUILD_TESTING=OFF','-DOPUS_BUILD_PROGRAMS=OFF']
            subprocess.run(flags,env=env,check=True)
            subprocess.run(['cmake','--build',str(output),'--parallel','4'],env=env,check=True)
            subprocess.run(['cmake','--install',str(output)],env=env,check=True)
        result=work/'result';result.mkdir()
        for name in NAMES:
            shutil.copyfile(prefix/'lib'/name,result/name)
            subprocess.run(['llvm-strip','--strip-unneeded',str(result/name)],check=True)
        report={'compiler':compiler,'api':26,'files':{n:hashlib.sha256((result/n).read_bytes()).hexdigest() for n in NAMES},'sources':sources}
        (result/'build.json').write_text(json.dumps(report,indent=2))
        result.rename(target)
    return target


if __name__=='__main__':
    print(build(json.loads((ROOT/'runtime-lock.json').read_text())))
