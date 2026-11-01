# OrBeats Android

A standalone Android companion for **OrBeats on PS4**: discover BeatSaver maps, preview and download songs, and manage the existing OrBeats song pack from your phone.

**Android8+ · ARM64 · Native Android UI · No PC or runtime Termux/server required**

Built on [Wkrotik's OrBeats](https://github.com/Wkrotik/OrBeats), reusing its conversion formats, console transactions and official plugin releases—not a replacement PS4 plugin. Original native/desktop documentation is preserved in [README-upstream.md](README-upstream.md).

## What it does

- Browse/search BeatSaver by **song name or exact map ID**; preview songs, view ratings/difficulties/download size, and save ZIPs to the phone library.
- Separate **On PS4 / On phone** libraries, with real indexed PS4 cover art and endpoint-specific cached snapshots.
- Mark known Noodle/Mapping Extensions incompatibilities red with reasons. **Unmarked does not mean guaranteed compatible**: the converter still validates downloaded charts/features.
- Prepare supported V2/V3/V4 maps and install a confirmed new song into the **existing OrBeats pack**, preserving older entries and OST/DLC. Requires the matching PS4 title/plugin/features and a legal conversion template; an existing verified song can provide one automatically.
- Choose **Original, Balanced or Small** audio quality. Original preserves eligible Vorbis packets without another lossy encode; smaller modes intentionally re-encode. Unsupported original profiles retain an honest PCM fallback, never bypass validation.
- Confirm removal of an indexed PS4 song separately from deleting a phone ZIP. Last-song removal retains its conversion template.
- Two separate Settings actions fetch/install/enable the **official main plugin or Extras** from Wkrotik/OrBeats GitHub releases, validating release manifest/hash/size/FSELF/version and preserving unrelated `plugins.ini` entries.
- Light/dark themes, springy buttons, open-source notices and an in-app console-linking tutorial.

## Audio sizes in 0.1.9

Actual Android APK conversion of the same159.64-second BeatSaver map (`25c63`), including its cover/menu preview:

| Quality | Song bundle | Bundle + menu files |
| --- | ---: | ---: |
| Original | 8.11 MB | 10.50 MB |
| Balanced — lossy | 2.87 MB | 5.26 MB |
| Small — lossy | 2.20 MB | 4.58 MB |

The older Android PCM bundle alone was28.33MB. These measurements are **one map, not universal size caps, fixed bitrates or measured installation-time guarantees**. Existing entries are not automatically recompressed/replaced. Choose quality before adding a new song.

Map details reports the **BeatSaver ZIP download size**, not installed size. If the CDN does not provide a size header and the ZIP is not on the phone yet, it says unavailable instead of downloading the entire file or guessing.

## Connecting safely

1. Update the APK **in place** to keep downloads/preferences/recovery. Do not uninstall or clear app data for a normal update.
2. Use GoldHEN FTP on a **trusted private LAN** and set the console address/port in Settings. Anonymous FTP is unencrypted; do not expose it to the internet.
3. Read the catalog first. Fully close Beat Saber before any install/removal/plugin change, and confirm the target/action in the app.
4. Keep the app open until the operation finishes; restart the game after success. Do not use another companion concurrently.
5. If an operation reports recovery/lock/rollback state, stop and inspect it. **Never blindly delete locks, clear app data or retry around the guard.**

Transactions retain snapshot checks, a writer lock, staged immutable uploads, full readback, durable recovery and index-last publication. Removal excludes the song from the index before deleting its exact files. Validation is not skipped for speed.

No songs, game-derived templates/assets or private signing keys are included. An empty installation still needs a legally obtained compatible template. Plugin buttons use the official upstream releases; unknown binaries/configuration states are refused.

## Status and testing

Download the signed **[OrBeats Android 0.1.9 release](https://github.com/HyperNfs/OrBeats-Android/releases/tag/v0.1.9)**. Install `OrBeats-0.1.9.apk` over your existing Android version; corresponding sources, dependency notices and SHA256 checksums are included. Do not confuse upstream desktop packages with the Android app.

- Host/parser/archive/header tests, package/signature/source-pin checks and16KiB native ELF checks pass.
- The actual APK's DEX/assets/AndroidPlatform/JNI passes V2/V3/V4 and real-map preparation, original44100/48000 Vorbis validation, selected-quality conversion, cover checks and Java bridges.
- Console installation/removal/plugin failure and rollback tests use **socket-forbidden simulated FTP**. They are not hardware proof.
- Earlier0.1.7 PCM installation/playback was user-confirmed. **New compressed PS4 playback, end-to-end timing and the updated installed UI remain hardware/visual test gates.**

See [Android README](android/README.md), [build/evidence notes](android/BUILD.txt) and [installed-device checklist](android/UI-CHECKLIST.md).

## Source and building

Android code, tests, build recipes, pinned dependency manifest and original corresponding sources live in [`android/`](android/). The original OrBeats source/history is retained at the repository root.

```sh
cd android
# Requires a provisioned ARM64 Termux Android/JDK toolchain described in README.md.
python tools/package_runtime.py --fetch  # explicit private, hash-verified dependency staging
bash build.sh
python development/conversion/runtime_apk_check.py
```

The runtime harness uses a developer simulated Application context; it does not install the Activity or prove console playback. Song/template/plugin test fixtures are deliberately not distributed. The app itself bundles its runtime and does not depend on Termux or a localhost service.

## Credits and licensing

- **Wkrotik / OrBeats**: original PS4 plugin, formats, converter, safe transactions and official release pipeline, GPL-3.0.
- **BeatSaver**: map API and community content; map authors retain their rights.
- Official **Chaquopy** Android Python runtime; **UnityPy**, **fsb5**, native Xiph audio libraries, SoundFile/libsoxr and other dependencies retain their original licenses and notices.

See [LICENSE](LICENSE), [Android license](android/LICENSE), [`runtime-lock.json`](android/runtime-lock.json) and the release `NOTICES.txt`/corresponding source archives. This is an independent companion, not affiliated with Beat Games, Meta or Sony.
