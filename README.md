<div align="center">

<img src="icon.svg" width="112" height="112" alt="OrBeats logo">

# OrBeats Android

**Your OrBeats library. Now in your pocket.**

Discover BeatSaver maps, build your library, and install custom songs on PS4—straight from your Android phone.

[![Download APK](https://img.shields.io/badge/Download_APK-v0.1.9-ABE28F?style=for-the-badge&logo=android&logoColor=101813&labelColor=26382C)](https://github.com/HyperNfs/OrBeats-Android/releases/download/v0.1.9/OrBeats-0.1.9.apk)
[![Android](https://img.shields.io/badge/Android-8%2B_%C2%B7_ARM64-26382C?style=for-the-badge)](#get-started)
[![License](https://img.shields.io/badge/License-GPL--3.0-26382C?style=for-the-badge)](LICENSE)

[Get started](#get-started) · [Audio quality](#audio-quality) · [Map support](#map-support) · [Releases](https://github.com/HyperNfs/OrBeats-Android/releases) · [Source](android/)

<sub>A standalone Android companion for <a href="https://github.com/Wkrotik/OrBeats">Wkrotik's OrBeats</a>. No PC, runtime Termux or localhost server required to use the app.</sub>

</div>

## Your next session, from your phone

- **Find your next map** with BeatSaver name or ID search, song previews, ratings and difficulty details.
- **Keep both libraries in view** with separate **On phone** and **On PS4** lists, real PS4 covers and cached catalog snapshots.
- **Choose your audio quality**: keep the original quality or trade some fidelity for smaller installs.
- **Manage your songs** with confirmed PS4 installation and removal, separate from deleting a phone download.
- **Install the official plugins** using separate **OrBeats** and **Extras** buttons, including `plugins.ini` registration.
- **Keep the originals**: custom songs stay in their own **OrBeats** pack alongside the stock soundtrack and DLC.
- **Make it yours** with light and dark themes, springy buttons and an in-app setup guide.

## Get started

You need **Android 8+ on an ARM64 phone**, plus **Beat Saber CUSA12878, patch 2.04**, on a PS4 with **GoldHEN plugin support and FTP enabled**. Other game builds are not supported.

1. [Download the APK](https://github.com/HyperNfs/OrBeats-Android/releases/download/v0.1.9/OrBeats-0.1.9.apk) and install it. **Updating? Install over your current version—don't uninstall or clear app data.**
2. Connect your phone and PS4 to the same trusted LAN. Enter the console's FTP address and port in **Settings**; the **?** button explains the connection steps.
3. Check your PS4 library. Use the separate official **OrBeats / Extras** install-update buttons if needed, then choose your preferred audio quality.
4. Download a map, open **Library → On phone → Install to PS4**, and confirm the target. After success, launch Beat Saber and open the **OrBeats** pack.

**First-time setup:** FTP alone is not enough. Conversion needs a legal, compatible template; an existing verified OrBeats song can supply one automatically. An empty setup still needs a legally obtained template. No game assets or templates are bundled.

> **Fully close Beat Saber before installing, removing songs or updating plugins.** Keep the app open until completion; don't run another companion at the same time. FTP is unencrypted—keep it on a trusted private LAN. If recovery or lock checks block an operation, stop and inspect it; don't blindly delete locks or clear app data.

## Audio quality

Choose **Settings → Audio quality** before preparing or installing a new song.

| Mode | What it does | Example size¹ |
| --- | --- | ---: |
| **Original** · default | Preserves eligible Vorbis audio without another lossy encode. | **10.50 MB** |
| **Balanced** | Lossy Vorbis encoding for a smaller file with a quality/size trade-off. | **5.26 MB** |
| **Small** | More aggressive lossy encoding to prioritize file size. | **4.58 MB** |

<sub>¹ Actual Android conversion of the same 159.64-second map, <code>25c63</code>, including cover and menu preview. The older PCM song bundle alone was 28.33 MB. Sizes vary by song; these are not fixed bitrates, universal caps or whole-install speed guarantees.</sub>

Downloaded ZIPs stay untouched. Existing PS4 songs aren't automatically recompressed or replaced. Unsupported original audio profiles may still use the larger PCM fallback; validation isn't skipped to force compression.

**Download size ≠ installed size.** Map details shows the BeatSaver ZIP size when the local file or CDN header provides it; otherwise it says unavailable.

## Map support

OrBeats Android converts supported vanilla **V2, V3 and V4** maps using the existing OrBeats pipeline. The matching plugin supports **up to 64 custom songs**; actual support depends on its negotiated capabilities.

**Chroma, Noodle Extensions, Mapping Extensions and custom environments are not supported.** Known incompatibilities are marked red with a reason, but an unmarked map is **not** guaranteed compatible—the downloaded charts still undergo strict checks. Unsupported features aren't silently stripped.

## Documentation

- [Android features, setup notes and build instructions](android/README.md)
- [Release notes, APK, sources and checksums](https://github.com/HyperNfs/OrBeats-Android/releases/tag/v0.1.9)
- [Build evidence and limitations](android/BUILD.txt) · [Device-test checklist](android/UI-CHECKLIST.md)
- [Original OrBeats desktop and PS4 documentation](README-upstream.md)
- [Report an Android bug or request a feature](https://github.com/HyperNfs/OrBeats-Android/issues)

<details>
<summary><strong>Testing, safety and building from source</strong></summary>

### What has been checked

- Host/parser/archive/header tests, package/signature/source-pin checks and 16 KiB native ELF alignment.
- Actual APK DEX/assets/AndroidPlatform/JNI conversion, including real maps, original 44.1/48 kHz Vorbis, selected audio quality, cover validation and Java bridges.
- Installation, removal, plugin deployment and rollback with **socket-forbidden simulated FTP**—not hardware proof. No console files were changed by the assistant during development.

Earlier **0.1.7 PCM installation/playback** was user-confirmed. **New compressed PS4 playback, whole-install timing and the updated installed UI still need hardware/visual testing.**

### Console safeguards

Explicit confirmations, closed-game checks, snapshot checks, writer locks, full readback and durable recovery remain in place. Installs publish the index last; removal excludes the song from the index before deleting its exact files and retains the last template. Official plugin artifacts are checked for release hash, size, format and version; unrelated configuration is preserved.

### Build the Android app

Android source and pinned dependencies live in [`android/`](android/). The original OrBeats source and history remain at the repository root.

```sh
cd android
# Requires the provisioned ARM64 Termux/JDK/Android build toolchain.
python tools/package_runtime.py --fetch
bash build.sh
python development/conversion/runtime_apk_check.py
```

See the [Android README](android/README.md) for prerequisites. The runtime harness uses a simulated Application context, not an installed Activity. Private song/template/plugin fixtures are not distributed. Termux is a **build environment**, not an app runtime requirement.

</details>

## Credits and license

Android adaptation maintained by **HyperNfs**, built on **[OrBeats by Wkrotik](https://github.com/Wkrotik/OrBeats)** and its existing PS4 plugin, converter and safe transaction pipeline—not a replacement plugin. Original OrBeats builds on [Beat Saber Deluxe by Chris Primeish and contributors](https://github.com/free5ty1e/BeatSaberPcCustomSongToPs4InstallConverter).

Thanks to BeatSaver and its map creators, GoldHEN, OpenOrbis, Chaquopy, UnityPy, fsb5, SoundFile/libsoxr and the Xiph projects. Dependencies retain their own licenses; see [GPL-3.0](LICENSE), the [Android license](android/LICENSE), [dependency manifest](android/runtime-lock.json) and release notices/corresponding sources.

Not affiliated with Beat Games, Meta or Sony. No music, game files, DLC, templates or private signing keys are distributed; song creators retain the rights to their work.
