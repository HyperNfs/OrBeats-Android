# OrBeats Android — 0.1.9 compressed audio, search selector and PS4 covers

## New in 0.1.9

- **Settings → Audio quality**: Original (default, no extra lossy encoding), Balanced or Small. Smaller modes use real streaming Vorbis encoding followed by the same full decoded-PCM/bundle checks; downloaded ZIPs and existing PS4 entries are untouched. Bitrate varies; these are not fixed-kbps or fixed-size promises. Pick quality before adding a new song; no automatic replacement/recompression of installed entries.
- Tested real25c63 sizes including cover/menu preview: **Original10.50MB / Balanced5.26MB / Small4.58MB**. Song bundle alone:8,111,012 /2,873,367 /2,195,585 bytes. Balanced/Small are lossy; compressed playback on PS4 remains a user-test gate. Sizes do not measure whole-install time.
- **Map details shows the BeatSaver ZIP download size**, using the local ZIP when available or a trusted bounded HEAD request otherwise. A server refusal/missing header leaves an explicit unavailable label; never guess installed size or download the full ZIP merely to measure it. The live25c63 size-header probe currently returned404; local ZIP size and simulated header/bounds/refusal tests pass.
- Shared button/icon/navigation presses and dialog action buttons now use the same springy release animation, including Settings controls. Android's animation-scale accessibility/system settings remain respected; installed-device visual testing is pending.

- Explicit **Search by name / Search by ID** selector. ID mode looks up one exact BeatSaver ID (e.g. `25975`); a missing ID returns no result rather than silently changing search modes. Name mode retains text search and pagination.
- **Library → On PS4** fetches real indexed cover images, verifies exact size/FNV, downsamples them and caches thumbnails on the phone. Refresh your PS4 library after updating to read the new cover metadata. Missing/offline/changed covers keep a placeholder; covers are read-only and do not require the game to be closed. The full library refresh still does.
- Supported original stereo Vorbis44100/48000 audio uses the same strict original-packet compressed FSB path as upstream OrBeats: no lossy re-encoding, validated codebooks, seek tables, independent decode and normalized-PCM comparison. Other sources/profiles retain PCM with the actual fallback reason. Full bundle validation/readback is NOT removed.
- Real map25c63 with the same private template: bundle **28,334,774 → 8,111,012 bytes** (about71.4% smaller). This measures bundle size, not whole-install speed; conversion, template download and FTP verification still take time. Installed PCM entries are NOT automatically recompressed/replaced. Test a new supported song; existing duplicate/no-op protection remains.
- Actual APK tests pass full44.1/48k compressed bundles, corruption/decoded-PCM refusal, WAV/FLAC fallback, real25c63 simulated installation, read-only cover integrity and Java byte-array bridge. Installed controls, compressed PS4 playback and end-to-end hardware timing remain user-test gates.

## Retained from 0.1.8

- Exact BeatSaver map-ID search (`25975`); only a direct lookup's HTTP404 falls back to text search.
- Known Noodle/Mapping Extensions maps and previously rejected unsupported chart features appear red with a reason. Unmarked maps are NOT guaranteed compatible; validation stays strict.
- On PS4 song details → **Remove from PS4** reads the current library and asks for confirmation. Upstream removes the index entry before exact owned-file cleanup; last-song removal retains the conversion template. Other songs/phone copies stay unchanged.
- Settings has TWO **Install/update OrBeats / Install/update Extras** buttons. Each explicitly confirms before downloading verified official stable artifacts and enabling its CUSA12878 plugins.ini entry. Existing library/features and unrelated INI entries are preserved; Extras needs main first. Unknown/newer binaries, locks and recovery state refuse replacement. No blind cleanup.
- The Settings Conversion engine self-test is removed; **Open-source notices** remains accessible. Internal conversion/developer tests remain.
- The existing upstream native FNV implementation is now packaged (API26/ARM64/16KiB). Actual Android16MiB checksum benchmark: Python5.147887s vs native0.028358s, identical wire checksum. This is CHECKSUM-ONLY, not181x overall installation. PCM conversion/uploads/full readback still take time and are not bypassed.
- 0.1.7's actual console installation/playback was user-confirmed.0.1.8 destructive operations are tested with socket-forbidden simulated FTP, NOT live writes or installed-screen proof.


A standalone native Android companion, using the supplied green OrBeats design as a reference. It does not load the removed website, run a localhost server or require Termux after installation.

## Install

Open `releases/0.1.9/OrBeats-0.1.9.apk` (or `build/OrBeats-0.1.9.apk`) on a **64-bit ARM (arm64-v8a), Android 8.0+** phone. **Install as an update over your existing OrBeats Android; do not uninstall/clear data.** Package ID and private storage paths are unchanged, version code increased to 10, and the build verifies the original signing certificate. Completed library items and preferences are not migrated or deleted.

This is a locally signed, unofficial preview, not a Play Store release. The user accepted the 0.1.2 UI on their phone. The assistant has not executed automated tests of the installed APK/Activity UI; separate standalone Android conversion probes are documented below.

## New in 0.1.7: PS4 songs in Library and cache-path fix

**Library → On PS4** now displays the existing pack's songs as individual title/artist rows. **On phone** retains your private downloads and their original actions. A read-only refresh saves an endpoint-specific catalog and last-read timestamp; the saved catalog is explicitly not a live connection. Settings' library result can open this view. Entering Library without a saved catalog can request a read-only check; installation still requires separate confirmation. A successful install attempts a catalog refresh, but refresh failure cannot turn a committed install into an installation error. Console entries are not fake local downloads and do not expose phone deletion/preparation actions. Since0.1.9 indexed covers are read and cached separately; full music/phone ZIPs are not downloaded for remote catalog rows.

The reported **25c63**, “this is what heartbreak feels like”, error named `HardStandard.dat`, although the official ZIP contains that exact file. The failure was reproduced in the actual APK using an aliased Android cache directory: upstream resolved the chart's path but compared it against an unresolved song directory, falsely treating it as an escape. The Android wrapper now resolves the extraction root and the upstream-facing generated temporary directory before the unchanged containment check. No chart is removed/renamed, no content hash is bypassed, and all 17 pinned upstream modules remain unmodified. Existing phone ZIPs need not be deleted.

Regression tests run the actual APK through an aliased Application/cache path. Real25c63 preparation (with/without a private template) and simulated installation pass:159.6363492063492seconds,Hard223/Expert475/ExpertPlus685 notes. Tests also cover V2/V3/V4 including generated V4 source directories, original score identity, old-entry/backup preservation, rollback and39-song catalog persistence/endpoint isolation. The template was obtained by authorized **read-only** verification of one installed bundle and is never distributed. These are developer-context tests, not installed Activity or live installation/playback evidence.

## Retained from 0.1.6: historical backups are not unfinished transactions

The 0.1.5 console check incorrectly refused ordinary `library.bin.backup-*` snapshots even with a valid current index. The reported connection error was an OrBeats guard failure, not failed FTP. Authorized read-only inspection confirmed a valid 39-song BSDALIB4 index and 40 historical BSDALIB1 backups, with no lock/rollback/stage markers. The fix follows upstream semantics: decode/validate the current index, leave historical backups untouched, and still refuse missing/corrupt main indexes, `.install-lock`, `library.bin.rollback-*` and `library.bin.stage-*`. Nothing is deleted, renamed or migrated to make a check pass. The error dialog now explains that FTP or library/setup validation may have failed rather than prescribing a connection fix for every refusal.

The actual APK regression tests now include 40 historical backups through read-only status, V3/V4 append, duplicate handling and failed transactions; backups stay byte-identical. Missing/corrupt index plus backups and genuine lock/rollback/stage markers still refuse. No real-console installation/playback has been performed by the assistant.

## Retained from 0.1.5: install into the existing OrBeats pack

Requires your already configured **OrBeats plugin, CUSA12878 patch 2.04**, a valid additive library index and GoldHEN anonymous FTP on a trusted LAN. 0.1.8 also offers separately confirmed official main/Extras installation and PS4 song removal. It never migrates a missing legacy index automatically.

1. Fully **close Beat Saber**. Keep GoldHEN FTP enabled, phone and console on the same trusted LAN.
2. Settings → enter the console IP/port → **Save & test console connection**. This now reads/verifies the plugin/capability, feature flags and existing `library.bin` and displays the installed song titles/count. It makes **no writes**. Choose **View Library**, or open **Library → On PS4 → Refresh PS4 library** to display installed songs.
3. Download a supported map (regression test: **25c63**, “this is what heartbreak feels like”; also tested **55710**, “Advanced BeatSaber Tutorial”, V4). Open **Library → On phone** and its details → **Install to PS4**. Review the console address and library count, then explicitly confirm **Install to this PS4**. Cancel makes no writes.
4. Keep this app open and the game closed throughout. The pinned upstream installer reads **one verified existing installed bundle** as its template automatically, prepares validated original Vorbis where supported, otherwise PCM, plus charts/media, uploads new immutable files with readback, and publishes the updated index **last**. Existing entries, OST/DLC and plugin/config remain untouched. An initialized empty library needs its retained `template.bundle` or a legal local template selected in Settings.
5. Only after success, launch/restart Beat Saber and open the **OrBeats** pack. Check the new song and older songs. 0.1.7 PCM playback was user-confirmed;0.1.9 compressed playback remains a hardware test gate. Simulated FTP is not hardware proof.

An active install lock, retained rollback/stage index-recovery files (not ordinary historical backup snapshots), changed confirmation snapshot, wrong plugin/capability or malformed/missing index causes refusal. There is no blind retry, automatic lock removal or automatic recovery. A cleanup failure after publication may mean the song was already committed; retained recovery files block a blind retry. On a lost connection/app termination, **keep the game closed; do not clear app data or remove a lock blindly**. Recovery journals/previous index bytes are retained under app-private `files/console-recovery/transactions`, not evictable cache. Android may kill the process; there is no foreground/background service. Thread interruption is respected before writing, but once the writer lock is attempted the worker finishes/rolls back rather than abandoning publication. FTP remains unencrypted.

## Retained from 0.1.4: local song preparation

Final UI fixes: carousel dots now blend width/color continuously with scrolling, and Android's bottom inset/navigation area matches the app's bottom bar in both themes. A preview stops when no copy of its song card is visible (vertically or in the carousel), when switching tabs, or starting a new search. Partial visibility keeps playing; duplicate visible cards for the same song also keep it playing.

1. Download a supported map from BeatSaver, then open **Library → On phone → song details → Load song**. For a known passing first test, search map ID **55710**, “Advanced BeatSaber Tutorial” (V4).
2. Keep OrBeats open during preparation. The result shows chart versions, duration, note counts and any skipped difficulties. Choose **Play prepared preview** or **Export preparation** to save a ZIP using Android's document picker.
3. Without a template, the ZIP contains normalized charts/audio, cover and preview. This is useful for testing the real input pipeline, but is **not a PS4 bundle**.
4. Optionally choose a legal compatible local bundle from your own existing OrBeats setup under **Settings → Conversion template (optional)**, then load the song again. Full output uses upstream original Vorbis where compatible or PCM fallback, and reopens/validates the generated Unity bundle and media before publication. No template is bundled, downloaded or exported.

The pinned OrBeats V2/V3/V4 version-aware importer/preparer is reused, including advanced V4 native charts, AudioData and lighting. Only its desktop decoder subprocess boundary is adapted to in-process SoundFile/libsoxr; no map scripts/plugins are executed. Unsupported requirements/custom metadata, invalid colors or negative beat positions are refused according to upstream rules, not stripped. BeatSaver's mod flags alone do not guarantee compatibility. For example, tested maps556de/55719 were refused for `_suggestions`,55718 for a negative beat and5570a for authored RGBA. Original downloaded ZIPs remain unchanged on failure.

Audio decoding/resampling is streamed, mono/stereo 8..192kHz → stereo PCM16 44100Hz, 1..600seconds. WAV/OGG/FLAC inputs are tested. Normalized intermediate/fallback PCM is about10.6MB/minute; compatible original Vorbis avoids uploading that expansion. Intermediate conversion still needs several hundred MB of free app storage. Prepared results are evictable cache, separate from the completed Library. Export anything you want to retain; reload if Android clears the cache. Batch conversion/cache quotas and background service are not implemented.

### Retained offline engine check

The developer-only `ConversionRuntime.check` starts the bundled official Chaquopy17.2/CPython3.13.16 runtime lazily, inside this APK. It tests UnityPy1.20.26 type-tree read/write/truncation, generated UnityFS edit/reopen in four pack modes, actual LZ4/Brotli and a generated512px PNG. It runs off the UI thread, uses only generated data and cleans its temporary files. First run may take a few seconds. Settings → **Open-source notices** opens the bundled dependency/source/license notices; the engine self-test button was removed at the user's request.

The developer check uses only generated data; real song preparation is the separate Library action. No console is contacted by either action. Optional proprietary desktop FMOD SDK binaries and the unused non-16KiB FreeType font backend are excluded; Pillow core PNG/JPEG is packaged. All shipped native ELF load segments are checked for16KiB alignment. Browsing, saved library paths, preview behavior and the accepted0.1.2 visual design are retained.

## Included

- Discover real BeatSaver maps: featured/curated, latest, best-rated, or text-search relevance, with pagination.
- Search songs/artists/mappers through BeatSaver's public API. No account required.
- Rounded cover art, BeatSaver rating percentages, difficulty details and audio previews. Tap to play/pause/resume; a loading preview shows a cancel icon. Completion/errors/backgrounding restore the play icon, and stale callbacks cannot take over a newer selection.
- Download maps to an app-private phone library; inspect or delete the phone copy.
- `?` opens a step-by-step console-linking tutorial. Settings saves a private IPv4 address/port and offers an explicit read-only existing OrBeats library check; remote installation requires a separate confirmation.
- Material 3 Expressive-inspired visual refresh: darker forest-green tonal surfaces, centered wordmark, prominent search field, compact animated navigation indicators, pill filter controls, vector icons, press feedback, featured artwork and scroll-aware carousel dots.
- Requested references: `uichange.png` annotations, `originalapp.png` colors/brand and `inspo.jpg` mobile spacing/navigation. These are local design references, not bundled APK content.
- Download/check controls appear on every song row, including narrow phones, alongside preview and map actions. The redundant header search icon is removed; the full search field remains. Settings actions have 12 dp gaps. All action targets remain at least 48 dp.
- Settings → **Light mode** switches to white/light-green surfaces, dark text/icons and matching native dialogs/system-bar icons. The choice survives app restart. It rebuilds only the UI, not the Activity or worker queues, so changing appearance does not intentionally cancel downloads/audio. Console field drafts and search text are retained.
- Ratings use BeatSaver's `stats.score`, NOT `upvotes / (upvotes + downvotes)`. Display is a single whole percentage without decimals: 82.9% → 82%, 88.7% → 88%. Missing/invalid scores say “No rating yet,” not an invented 100%. Scores reflect the API response (saved library metadata is a snapshot); live votes can change after a screenshot.
- Latest local references: `uifix.png`, `settingsui.png`, `wrongpercent.jpg`; none are bundled in the APK/source archive.

The visual direction is implemented with native platform widgets/vectors/animations, **not the official Compose/Material 3 Expressive component library**. This is a styled native implementation, not a claim of Google certification or pixel-identical component behavior.

## Important limitations

**Console installation is experimental and requires your explicit confirmation.** A raw BeatSaver ZIP or exported preparation is NOT an installable package; use the guarded Install to PS4 flow. Local prepared manifests retain upstream `runtime_ready:false` and do not prove hardware playback. Neither simulated FTP tests nor local bundle validation guarantees your console/runtime compatibility. No game templates or proprietary FMOD SDK payloads are bundled. Only explicitly confirmed official main/Extras deployment/INI enable and exact PS4 song removal are included; no batch queue, automatic game launch or legacy migration.

Downloads live in this application's private storage. They are managed inside Library, not saved into Android's public Downloads directory. Uninstalling or clearing app data deletes them. Install future updates over this app with the same signing key to preserve data. Keep the app open during downloads; no background download service/notifications are implemented. Interrupted temporary downloads are cleaned on the next launch. A validated ZIP here only means safe archive structure/CRC/size bounds, not that every map is supported by PS4 Beat Saber.

The FTP library check logs in, lists and reads fixed OrBeats/plugin/index paths; it never uploads/deletes/renames. The separately confirmed installer stages/reads/renames only existing protocol-owned additive files and its writer lock. FTP is unencrypted: use only your trusted private LAN, never port-forward it to the Internet. Beat Saber must be fully closed for both the full library check and installation.

Network/CPU tasks run off the UI thread. Cover requests, bytes, image decode dimensions, ZIP entries/expanded bytes and FTP replies are bounded. Android system process termination may still cancel a phone download; existing completed library items are not replaced during download publication. BeatSaver rate limits/errors are displayed without automatic retry loops.

## Build on this Termux phone

```
cd /storage/emulated/0/projects/OrBeatsAndroid
# First time only: explicitly fetch SHA256-pinned public runtime prerequisites privately
python tools/package_runtime.py --fetch
bash build.sh
# Optional: includes a real HTTPS request to BeatSaver
bash build.sh --live
```

The offline build verifies `runtime-lock.json` SHA256 pins, builds modern Ogg1.3.6/Vorbis1.3.7/FLAC1.5.0/Opus1.5.2/libsndfile1.2.2 sources privately with the existing ARM64 clang/cmake/Ninja toolchain (API26 target,16KiB, no Termux RPATH or extra host dependencies), then packages official Chaquopy Java/JNI/assets with the existing manual aapt/D8 toolchain (no Gradle/SDK switch or custom runtime installer), runs Core/preview/packager assertions, compiles Java8 against Android API35, aligns/signs/verifies the APK and writes `build/SHA256SUMS`. `.imy` assets are ZIP_STORED as required by upstream; native libraries are extracted by Android (`extractNativeLibs=true`). This is an arm64-only APK. Runtime downloads occur only during the explicit build-time `--fetch`, never inside the app.

Tools were downloaded/extracted locally under `$HOME/.cache/orbeats-android-tools`:

- Termux packages: openjdk-21 21.0.13, aapt 16.0.0.4-4, apksigner 37.0.0, fmt 12.2.0, libpng 1.6.59 and libzopfli 1.0.3-5.
- Android API 35 jar: `https://raw.githubusercontent.com/Sable/android-platforms/master/android-35/android.jar` (third-party mirror of the Android platform stubs; build-only).
- D8/R8 8.7.18: `https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.7.18/r8-8.7.18.jar`.

`TOOLS-SHA256SUMS` records the exact downloaded build inputs. These SDK/JDK files are not bundled in the APK/source archive. The build expects the staged tools; it does not silently apt-install packages or download SDKs. A fresh Termux environment must stage the same tools and their runtime dependencies first (`apt download`, then `dpkg-deb -x` into the private tools root, not system installation). `ORBEATS_ANDROID_TOOLS` can point to another staged tools directory.

**Preserve** `$HOME/.local/share/orbeats-android/signing.jks` privately for update compatibility. It is deliberately outside shared storage and the source package. The local development keystore uses the standard development password `android`; the private file itself must remain private. Do not distribute it. If it is lost, a newly signed build cannot update this installation without uninstalling/losing private app data first.

## Validation status

Passed: 91 Core host checks including score truncation/invalid values/decimal-boundary regressions and real BeatSaver HTTPS search; 21 preview-state checks covering loading/cancel/play/pause/resume, completion reset and stale tokens; Java/D8/vector-resource compilation; APK integrity, launcher/version/permissions, alignment and APK v2/v3 signature verification. Build also compares the signing certificate against 0.1.0 to prevent an incompatible update. Static checks verify shared rating-source use, requested controls, theme/palette consistency and WCAG 4.5:1 normal-text contrast for the selected light/dark color pairs. Static checks do not execute the switch or Android layout.

The new APK's actual DEX/assets/native libraries also pass `python development/conversion/runtime_apk_check.py`: Android `app_process`, real AssetManager, official AndroidPlatform/Java↔Python JNI, the production engine check twice, temporary cleanup and interruption refusal. That harness supplies a developer Application/preferences context; it is **not an installed APK/Activity/lifecycle test**. Package checks cover ABI/ELF16KiB, dependency/cache hashes, required engine classes, notices, and exclusion of FMOD/desktop binaries/private keys. Build-only packager regressions cover unsafe paths and wrong-ABI/4KiB/misaligned ELF refusal.

The user's 0.1.2 UI approval and installed0.1.3 engine-check success (`result.jpg`) are recorded. The assistant has not independently verified installed0.1.5 update/data retention, Load song/SAF dialogs, prepared-preview MediaPlayer playback, large-font rendering, lifecycle, UI-driven phone downloads or live PS4 login. There is no emulator/ADB available in this session. The pure preview-state tests do NOT execute Android MediaPlayer. See `UI-CHECKLIST.md`; local checks must not be described as device testing.

## Conversion development and remaining gates

`development/conversion/README.md` retains the historical PCM/ART/native writer evidence and documents the0.1.4 song harness. Actual signed APK code/assets/native libraries pass six synthetic V2/V3/V4 preparations, with and without a private compatible template, including full SerializedFile/PCM/media validation, cache reuse/repair, content-hash refusal and Java bridge checks. A real downloaded V4 map55710 also passes with/without template:153.2852380952381seconds,136ExpertPlus notes. This uses a developer Application context, **not installed Activity or PS4 playback testing**. Original releases/evidence remain immutable. No template/music is included in the APK/source archive and no PS4 connection/writes occur during these tests.

The eleven ConsoleLibrary host tests cover private addresses/ports, confirmation gating, cancellation/write boundaries, bounded connection timeout, directory-listing byte/entry limits and transfer deadlines. The actual APK's real pinned installer also runs with a socket-forbidden, in-memory FTP: V2/V3/V4, nonempty auto-template append, initialized empty library retained/local template, old entry preservation, original V4 score identity, duplicate no-op, index-last publication, persistent journals and refusal/rollback cases. Production Java status/install methods are tested against that same simulation, never a real console.

The14 SongLoader host tests cover ZIP/path/duplicate/symlink/Info bounds, cancellation/hash refusal, exact decoder command allowlist and UnityFS template bounds/expansion/truncation. Native tests also guard the ObjectReader shallow-copy regression. Remaining gates: user's installed Load song/preview/export, broader valid-map/API/device matrix, broader device/profile coverage, installed selector/covers and real Android→PS4 compressed installation/playback. Original Vorbis packet/seek/full-bundle handling now passes actual APK developer-context tests; other sources still use PCM fallback. These tests do not establish recovery after every possible network/process failure.

## Source/provenance

GPL3 Java UI/network/archive/bridge and Python adapter. The APK includes21 unmodified GPL OrBeats preparation/installer/transaction/score/management/release helper modules plus its unmodified FNV C source/native library and required source data at commit `098897736e089107704ec1633daff8922087fcc8`, not its server or native PS4 plugin. Scoped Android bindings supply in-process audio, bounded template checks, strict existing-index reads, original verified score hashes and persistent recovery storage; the upstream installer algorithm remains unchanged. Official Chaquopy17.2.0/CPython3.13.16 supplies the runtime. UnityPy1.20.26 uses its supported no-Boost fallback plus an explicit minimal ObjectReader absent-reader/AttributeError compatibility patch needed for `copy.copy`; SoundFile0.13.1 has the documented one-line Android native-loader patch. Both patches are in `development/conversion/patches` and described in bundled notices. Other dependencies include pinned NumPy/CFFI/libsoxr, unmodified MIT fsb5-1.0 Python sources for Vorbis packet reconstruction, and modern source-built Xiph/libsndfile decoders. fsb5 and its license/source hashes match upstream's documented provenance. Optional FMOD binaries and the unused FreeType/font backend are omitted, not stubbed. `runtime-lock.json` records URLs/SHA256; source-built audio has its recipe in `tools/build_audio.py` and corresponding pinned source tarballs in the release's `native-audio-sources.zip`. Settings → Open-source notices opens the original notices/licenses. BeatSaver supplies remote map metadata, covers and previews; individual creators retain their rights. The APK includes no song payloads or analytics. Only the Android INTERNET permission is requested. This app is an unofficial independent preview, not an official BeatSaver app.

Application source is GPL-3.0; see `LICENSE`. Build-tool dependencies and BeatSaver content retain their own licenses/terms.
