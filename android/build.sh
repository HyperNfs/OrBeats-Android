#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
TOOLS="${ORBEATS_ANDROID_TOOLS:-$HOME/.cache/orbeats-android-tools}"
PREFIX_LOCAL="$TOOLS/root/data/data/com.termux/files/usr"
export LD_LIBRARY_PATH="$PREFIX_LOCAL/lib:${PREFIX:-/data/data/com.termux/files/usr}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
JAVA="$PREFIX_LOCAL/lib/jvm/java-21-openjdk/bin"
ANDROID="$TOOLS/android.jar"
R8="$TOOLS/r8.jar"
for path in "$JAVA/javac" "$JAVA/java" "$JAVA/keytool" "$PREFIX_LOCAL/bin/aapt" "$PREFIX_LOCAL/bin/zipalign" "$ANDROID" "$R8" "$PREFIX_LOCAL/share/java/apksigner.jar"; do
    test -f "$path" || { echo "Missing build tool: $path" >&2; exit 1; }
done
APK=build/OrBeats-0.1.9.apk
python tools/package_runtime.py
python tests/RuntimePackagingTest.py
python tests/SongLoaderTest.py
python tests/ConsoleLibraryTest.py
mkdir -p build/classes build/tests build/dex build/generated
find build/classes build/tests build/dex build/generated -type f -delete
"$JAVA/javac" --release 8 -encoding UTF-8 -d build/tests src/dev/orbeats/android/Core.java src/dev/orbeats/android/PreviewState.java tests/CoreTest.java tests/PreviewStateTest.java
"$JAVA/java" -ea -cp build/tests dev.orbeats.android.CoreTest "${1:-}"
"$JAVA/java" -ea -cp build/tests dev.orbeats.android.PreviewStateTest
"$PREFIX_LOCAL/bin/aapt" package -f -m -J build/generated -M AndroidManifest.xml -S res -I "$ANDROID" -F build/resources.apk
"$JAVA/javac" --release 8 -encoding UTF-8 -cp "$ANDROID:build/runtime/chaquopy_java.jar" -d build/classes src/dev/orbeats/android/*.java build/generated/dev/orbeats/android/R.java
python - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
with ZipFile('build/classes.jar','w',ZIP_DEFLATED) as archive:
    for file in sorted(Path('build/classes').rglob('*.class')):
        archive.write(file,file.relative_to('build/classes'))
PY
"$JAVA/java" -cp "$R8" com.android.tools.r8.D8 --lib "$ANDROID" --min-api 26 --output build/dex build/classes.jar build/runtime/chaquopy_java.jar
python - <<'PY'
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
shutil.copyfile('build/resources.apk','build/unsigned.apk')
with ZipFile('build/unsigned.apk','a',ZIP_STORED) as archive:
    for file in sorted(Path('build/dex').glob('*.dex')):
        archive.write(file,file.name)
    for folder in ['assets','lib']:
        for file in sorted(Path('build/runtime',folder).rglob('*')):
            if file.is_file():
                archive.write(file,str(file.relative_to('build/runtime')),compress_type=ZIP_STORED if file.suffix=='.imy' else ZIP_DEFLATED)
PY
"$PREFIX_LOCAL/bin/zipalign" -f 4 build/unsigned.apk build/aligned.apk
KEY="$HOME/.local/share/orbeats-android/signing.jks"
mkdir -p "$(dirname "$KEY")"
chmod 700 "$(dirname "$KEY")"
if ! test -f "$KEY"; then
    test ! -f releases/0.1.0/OrBeats-0.1.0.apk || { echo 'Missing original signing key: refusing an incompatible update' >&2; exit 1; }
    "$JAVA/keytool" -genkeypair -keystore "$KEY" -storepass android -keypass android -alias orbeats-local -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=OrBeats Android local build'
    chmod 600 "$KEY"
fi
"$JAVA/java" -jar "$PREFIX_LOCAL/share/java/apksigner.jar" sign --ks "$KEY" --ks-key-alias orbeats-local --ks-pass pass:android --key-pass pass:android --out "$APK" build/aligned.apk
"$JAVA/java" -jar "$PREFIX_LOCAL/share/java/apksigner.jar" verify --verbose --print-certs "$APK" | tee build/signature.txt
if test -f releases/0.1.0/OrBeats-0.1.0.apk; then
    "$JAVA/java" -jar "$PREFIX_LOCAL/share/java/apksigner.jar" verify --print-certs releases/0.1.0/OrBeats-0.1.0.apk > build/previous-signature.txt
    python - <<'PY'
from pathlib import Path
import re
def certificate(path):
    return re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', Path(path).read_text())
assert certificate('build/signature.txt') == certificate('build/previous-signature.txt') != []
print('PASS: signing certificate matches 0.1.0; compatible in-place update')
PY
fi
"$PREFIX_LOCAL/bin/zipalign" -c -v 4 "$APK"
"$PREFIX_LOCAL/bin/aapt" dump badging "$APK"
python tests/check_apk.py "$PREFIX_LOCAL/bin/aapt" "$APK"
(cd build && sha256sum "${APK#build/}" > SHA256SUMS)
echo "Built $APK (arm64). Installed APK UI/runtime check NOT device-tested by this build."
