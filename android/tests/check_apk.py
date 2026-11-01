#!/usr/bin/env python3
"""Static package assertions, not Android UI/runtime tests."""
import hashlib
import io
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

root = Path(__file__).resolve().parent.parent
manifest = ET.parse(root / 'AndroidManifest.xml').getroot()
a = '{http://schemas.android.com/apk/res/android}'
assert manifest.attrib['package'] == 'dev.orbeats.android'
assert manifest.get(a+'versionCode') == '10' and manifest.get(a+'versionName') == '0.1.9'
assert manifest.find('uses-sdk').get(a+'minSdkVersion') == '26'
assert manifest.find('uses-sdk').get(a+'targetSdkVersion') == '35'
assert [p.get(a+'name') for p in manifest.findall('uses-permission')] == ['android.permission.INTERNET']
app = manifest.find('application')
assert app.get(a+'allowBackup') == 'false'
assert app.get(a+'extractNativeLibs') == 'true'
assert app.get(a+'usesCleartextTraffic') == 'false'
assert app.find('activity').get(a+'name') == '.MainActivity'
assert app.find('activity').get(a+'exported') == 'true'
assert not app.findall('service') and not app.findall('provider')
with ZipFile(sys.argv[2]) as apk:
    assert apk.testzip() is None
    assert {'AndroidManifest.xml', 'resources.arsc', 'classes.dex', 'res/drawable/icon.xml'} <= set(apk.namelist())
    assert not any(n.endswith(('.jks','.keystore','.zip')) for n in apk.namelist())
    sys.path.insert(0, str(root/'tools'))
    from package_runtime import elf_16k
    expected_libs={'libchaquopy_java.so','libcrypto_chaquopy.so','libcrypto_python.so',
                   'libpython3.13.so','libpython3.so','libsqlite3_chaquopy.so',
                   'libsqlite3_python.so','libssl_chaquopy.so','libssl_python.so'}
    assert {n for n in apk.namelist() if n.startswith('lib/')} == {'lib/arm64-v8a/'+n for n in expected_libs}
    for name in apk.namelist():
        if name.endswith('.so'): elf_16k(apk.read(name))
        if name.endswith('.imy'): assert apk.getinfo(name).compress_type == ZIP_STORED
    build=json.loads(apk.read('assets/chaquopy/build.json'))
    assert build['python_version']=='3.13' and build['extract_packages']==['orbeats_pipeline']
    for name, sha in build['assets'].items():
        assert hashlib.sha1(apk.read('assets/chaquopy/'+name)).hexdigest()==sha
    with ZipFile(io.BytesIO(apk.read('assets/chaquopy/requirements-arm64-v8a.imy'))) as requirements:
        assert {'UnityPy/__init__.py','PIL/Image.py','attrs/__init__.py','lz4/block/_block.so','_brotli.so','fsb5/__init__.py','fsb5/vorbis.py'} <= set(requirements.namelist())
        import tarfile
        pin=next(e for e in json.loads((root/'runtime-lock.json').read_text()) if e['kind']=='fsb5')
        data=(Path.home()/'.cache/orbeats-android-tools'/pin['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==pin['sha256']
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as source:
            for member in source.getmembers():
                name=member.name.removeprefix('fsb5-1.0/')
                if member.isfile() and name.startswith('fsb5/') and name.endswith('.py'):assert requirements.read(name)==source.extractfile(member).read()
        assert b'Copyright (c) 2016 Simon Pinfold' in apk.read('assets/NOTICES.txt')
        assert not any('/FMOD/' in n or n.endswith(('.dll','.dylib','.exe')) for n in requirements.namelist())
        assert 'PIL/_imagingft.so' not in requirements.namelist()  # No optional non-16K FreeType backend.
        from build_audio import NAMES as audio_libs
        assert {'chaquopy/lib/'+n for n in audio_libs} <= set(requirements.namelist())
        assert 'chaquopy/lib/libFLAC++.so' not in requirements.namelist()
        for name in requirements.namelist():
            if name.endswith('.so'): elf_16k(requirements.read(name))
        # New phone-built decoders must never resolve Termux or unshipped dependencies.
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            for name in audio_libs:
                path=Path(directory)/name; path.write_bytes(requirements.read('chaquopy/lib/'+name))
                dynamic=subprocess.check_output(['llvm-readelf','-d',str(path)],text=True)
                assert 'RPATH' not in dynamic and 'RUNPATH' not in dynamic
                assert set(re.findall(r'Shared library: \[([^]]+)\]',dynamic)) <= set(audio_libs)|{'libc.so','libm.so','libdl.so'}
                assert 'Library soname: ['+name+']' in dynamic
    with ZipFile(io.BytesIO(apk.read('assets/chaquopy/app.imy'))) as modules:
        assert {'conversion_runtime.py','writer_probe.py','song_loader.py','orbeats_pipeline/development/scripts/prepare_additive_bundle.py','orbeats_pipeline/development/scripts/import_v2_additive.py','orbeats_pipeline/development/scripts/import_v3_additive.py','orbeats_pipeline/development/scripts/import_v4_additive.py','orbeats_pipeline/tools/additive_v4_native.py'} <= set(modules.namelist())
        assert not any(n.endswith('.bundle') or n.endswith('console_library_probe.py') for n in modules.namelist())
        assert {'console_library.py','orbeats_pipeline/tools/additive_companion.py','orbeats_pipeline/tools/console_transaction.py','orbeats_pipeline/tools/score_source.py'} <= set(modules.namelist())
        assert modules.read('writer_probe.py')==(root/'development/conversion/tests/android_writer.py').read_bytes()
        for path in (root/'python').glob('*.py'):
            assert modules.read(path.name)==path.read_bytes()
        from package_runtime import CACHE
        pinned=next(e for e in json.loads((root/'runtime-lock.json').read_text()) if e['kind']=='orbeats')
        original=(CACHE/pinned['file']).read_bytes()
        assert hashlib.sha256(original).hexdigest()==pinned['sha256']
        selected=[n for n in modules.namelist() if n.startswith('orbeats_pipeline/') and n.endswith('.py') and not n.endswith('__init__.py')]
        assert len(selected)==21
        selected+=['orbeats_pipeline/tools/native/fnv.c','orbeats_pipeline/src/main.cpp']
        native=modules.read('orbeats_pipeline/tools/native/orbeats_hash.so')
        from package_runtime import elf_16k
        elf_16k(native)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'orbeats_hash.so';path.write_bytes(native)
            dynamic=subprocess.check_output(['llvm-readelf','-d',str(path)],text=True)
            assert 'RPATH' not in dynamic and 'RUNPATH' not in dynamic
            assert set(re.findall(r'Shared library: \[([^]]+)\]',dynamic)) <= {'libc.so','libm.so','libdl.so'}
        with ZipFile(io.BytesIO(original)) as upstream:
            for name in selected:
                matches=[n for n in upstream.namelist() if n.endswith('/orbeats/'+name.split('/',1)[1])]
                assert len(matches)==1 and modules.read(name)==upstream.read(matches[0])
    notices=apk.read('assets/NOTICES.txt')
    assert b'GNU GENERAL PUBLIC LICENSE' in notices and b'Python Software Foundation' in notices
    assert b'Chaquo Ltd' in notices and b'UnityPy' in notices and b'Independent JPEG Group' in notices
    dex = apk.read('classes.dex')
    assert dex.startswith(b'dex\n')
    assert b'Ldev/orbeats/android/MainActivity;' in dex
    assert b'Ldev/orbeats/android/Core;' in dex
    assert b'Ldev/orbeats/android/PreviewState;' in dex
    assert b'Ldev/orbeats/android/ConversionRuntime;' in dex and b'Lcom/chaquo/python/android/AndroidPlatform;' in dex
    assert b'Search by name' in dex and b'Search by ID' in dex
    assert b'Conversion engine (experimental)' not in dex and b'Load song' in dex and b'Export preparation' in dex
    assert all(label in dex for label in (b'Open-source notices',b'Install/update OrBeats',b'Install/update Extras',b'Remove from PS4',b'https://api.beatsaver.com/maps/id/',b'Noodle Extensions'))
    for icon in ('search','help','download','check','play','pause','close','more','tune','explore','library','settings'):
        assert 'res/drawable/ic_'+icon+'.xml' in apk.namelist()
    assert b'Landroid/webkit/WebView;' not in dex
    assert b'https://api.beatsaver.com/search/text/' in dex
    assert b'Link your PS4' in dex
    assert b'USER anonymous' in dex and b'QUIT' in dex
    assert b'Light mode' in dex and b'lightMode' in dex
    assert b'Ljava/math/BigDecimal;' in dex
# Regression checks for native themes and the shared rating source; not device execution.
source = (root / 'src/dev/orbeats/android/MainActivity.java').read_text()
rating = source.split('private String rating(', 1)[1].split('\n', 1)[0]
assert 'Core.scorePercent' in rating and 'optDouble("score"' in rating
assert 'upvotes' not in rating and 'downvotes' not in rating and 'Math.round' not in rating
header = source.split('LinearLayout actions=row();', 1)[1].split('search=new EditText', 1)[0]
assert 'ic_help' in header and 'ic_search' not in header
rows = source.split('private LinearLayout songCard(', 1)[1].split('private ImageButton previewButton', 1)[0]
assert 'widthPixels>=' not in rows and 'card.addView(downloadButton)' in rows
assert 'putBoolean("lightMode",checked)' in source and 'recreate()' not in source
assert 'addOnPreDrawListener' in source and '!visibleSong(list,playback.mapId))stopPreview()' in source
assert 'if(renderedTab>=0&&renderedTab!=tab)stopPreview();' in source
assert 'if(reset){stopPreview();page=0;maps.clear();}' in source
assert source.count('card.setTag("song:"+map.optString("id"))')==2
assert 'if(view.getVisibility()!=View.VISIBLE)return false;' in source
assert 'getGlobalVisibleRect(new Rect())' in source
assert '1-Math.abs(position-i)' in source and 'colors.evaluate(weight,TONAL,GREEN)' in source
assert 'bottom.setPadding(0,0,0,insets.getSystemWindowInsetBottom())' in source
assert 'setNavigationBarContrastEnforced(false)' in source and 'setNavigationBarDividerColor(BAR)' in source
assert 'installProgress=dialog()' in source and '.setCancelable(false).show()' in source
assert source.count('new AlertDialog.Builder(this)')==1 and 'up.setInterpolator(new OvershootInterpolator(1.1f))' in source
assert 'Audio quality: ' in source and 'Core.downloadSize(' in source and 'dialog.isShowing()' in source
assert source.count('installProgress.dismiss();installProgress=null;')==5
assert 'rememberIncompatibility(map,error)' in source and 'metadataIncompatibility' in source
assert 'if(error.status!=404)throw error;' in source
palette = {name: (light, dark) for name, light, dark in re.findall(r'\b(BG|BAR|CARD|TONAL|GREEN|WHITE|MUTED)=lightMode\?0xff([0-9a-f]{6}):0xff([0-9a-f]{6})', source)}
assert len(palette) == 7
styles = {style.get('name'): {item.get('name'): item.text for item in style} for style in ET.parse(root/'res/values/styles.xml').getroot()}
assert styles['LightTheme']['android:forceDarkAllowed'] == 'false'
def luminance(hex_color):
    channels = [int(hex_color[i:i+2],16)/255 for i in (0,2,4)]
    channels = [c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4 for c in channels]
    return sum(c*w for c,w in zip(channels,(0.2126,0.7152,0.0722)))
for mode, name in enumerate(('LightTheme','AppTheme')):
    style = styles[name]
    for attr, color in [('colorAccent','GREEN'),('textColorPrimary','WHITE'),('textColorSecondary','MUTED'),('windowBackground','BG'),('colorBackgroundFloating','BAR')]:
        assert style['android:'+attr].lower() == '#'+palette[color][mode]
    assert style['android:windowLightStatusBar'] == ('true' if mode==0 else 'false')
    assert style['android:windowLightNavigationBar'] == ('true' if mode==0 else 'false')
    for foreground, background in [('WHITE','BG'),('WHITE','BAR'),('WHITE','CARD'),('MUTED','BG'),('MUTED','BAR'),('MUTED','CARD'),('GREEN','TONAL'),('GREEN','CARD'),('BG','GREEN')]:
        a1,b1=sorted([luminance(palette[foreground][mode]),luminance(palette[background][mode])])
        assert (b1+0.05)/(a1+0.05)>=4.5, (name,foreground,background)
print('PASS: theme resource/palette consistency, light/dark text contrast, shared score source and requested control regressions (static only)')
badging = subprocess.check_output([sys.argv[1], 'dump', 'badging', sys.argv[2]], text=True)
assert "name='dev.orbeats.android'" in badging
assert "versionCode='10'" in badging and "versionName='0.1.9'" in badging
assert re.findall(r"native-code: (.*)",badging)==["'arm64-v8a'"]
assert "sdkVersion:'26'" in badging and "targetSdkVersion:'35'" in badging
assert "launchable-activity: name='dev.orbeats.android.MainActivity'" in badging
assert re.findall(r"uses-permission: name='([^']+)'", badging) == ['android.permission.INTERNET']
print('PASS: APK/DEX/SDK/launcher/only-INTERNET; pinned Chaquopy assets, ARM64/ELF16KiB, no FMOD/desktop binaries/WebView/signing key')
print('NOT TESTED: Android lifecycle, visual layout, audio playback, phone download UI or live console login')
