#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Run actual APK DEX/assets/JNI through app_process with a developer Context.

No APK installation, Activity lifecycle, server, user songs or console connection.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(os.environ.get('ORBEATS_ANDROID_TOOLS', str(Path.home()/'.cache/orbeats-android-tools')))


def main():
    apk = (ROOT/'build/OrBeats-0.1.9.apk').resolve()
    work = Path(tempfile.mkdtemp(prefix='apk-runtime-', dir=TOOLS))
    (work/'context-real').mkdir()
    (work/'context').symlink_to(work/'context-real', target_is_directory=True)
    prefix = TOOLS/'root/data/data/com.termux/files/usr'
    java = prefix/'lib/jvm/java-21-openjdk/bin'
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = str(prefix/'lib')+':'+os.environ.get('PREFIX','/data/data/com.termux/files/usr')+'/lib'
    classes=work/'classes';classes.mkdir()
    cp = str(TOOLS/'android.jar')+':'+str(ROOT/'build/classes')+':'+str(ROOT/'build/runtime/chaquopy_java.jar')
    subprocess.run([str(java/'javac'),'--release','8','-cp',cp,'-d',str(classes),
                    str(ROOT/'development/conversion/tests/RuntimeApkTest.java')],env=env,check=True)
    jar=work/'test.jar'
    with ZipFile(jar,'w',ZIP_DEFLATED) as z:
        for f in classes.rglob('*.class'):z.write(f,str(f.relative_to(classes)))
    dex=work/'dex';dex.mkdir()
    subprocess.run([str(java/'java'),'-cp',str(TOOLS/'r8.jar'),'com.android.tools.r8.D8',
                    '--lib',str(TOOLS/'android.jar'),'--classpath',str(ROOT/'build/classes.jar'),
                    '--classpath',str(ROOT/'build/runtime/chaquopy_java.jar'),
                    '--min-api','26','--output',str(dex),str(jar)],env=env,check=True)
    runner=work/'runner.jar'
    with ZipFile(runner,'w',ZIP_DEFLATED) as z:z.write(dex/'classes.dex','classes.dex')
    private_apk=work/'app.apk';shutil.copyfile(apk,private_apk)
    native=work/'native';native.mkdir()
    with ZipFile(private_apk) as z:
        for name in z.namelist():
            if name.startswith('lib/arm64-v8a/') and name.endswith('.so'):
                (native/Path(name).name).write_bytes(z.read(name))
    runner.chmod(0o444);private_apk.chmod(0o444)
    env['CLASSPATH']=str(runner)+':'+str(private_apk)
    env['LD_LIBRARY_PATH']=str(native)+':'+env['LD_LIBRARY_PATH']
    env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    cmd=['/system/bin/app_process','-Djava.library.path='+str(native),'/system/bin',
         'dev.orbeats.android.RuntimeApkTest',str(private_apk),str(work/'context'),str(native)]
    if sys.argv[1:]:
        if len(sys.argv)!=3 or sys.argv[1]!='--song-template':raise SystemExit('Usage: runtime_apk_check.py [--song-template PRIVATE_LOCAL_BUNDLE]')
        template=Path(sys.argv[2]).resolve()
        if not template.is_file():raise SystemExit('Missing private local template')
        env['ORBEATS_SONG_PROBE_ROOT']=str(work/'context/cache/song-probe')
        env['ORBEATS_SONG_PROBE_TEMPLATE']=str(template)
        cmd.append(str(ROOT/'development/conversion/tests/song_loader_probe.py'))
        cmd.append(str(ROOT/'development/conversion/tests/console_library_probe.py'))
    print('Developer APK runtime workspace:',work,flush=True)
    print('APK SHA256:',hashlib.sha256(private_apk.read_bytes()).hexdigest(),flush=True)
    with (work/'RUN.txt').open('w') as log:
        process=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    print((work/'RUN.txt').read_text())
    if process.returncode:
        raise SystemExit('APK runtime harness failed: '+str(process.returncode))
    report=work/'context/RESULT.txt'
    print(report.read_text())
    print('PASS: APK code/assets + official AndroidPlatform/Java JNI; NOT installed APK UI/lifecycle')


if __name__ == '__main__':main()
