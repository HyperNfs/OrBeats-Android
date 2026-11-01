# Android conversion — 0.1.9 compressed audio and historical proofs

## Current 0.1.9 evidence

Actual signed APK2556069b3af974917e831af46455f3724bcb8d92bc30975645d5f059a20da48d passes original44100/48000 Vorbis full bundles, packet/seek/codebook reconstruction, independent decode and normalized-PCM comparison, corruption/wrong-PCM refusals, WAV/FLAC fallback, real25c63 preparation/simulated install, cover integrity and Java bridging.21 pinned OrBeats modules and five MIT fsb5-1.0 modules remain unmodified. Scoped FunctionType verifier binds ONLY its exact decoder command to native SoundFile/libsoxr; no stdlib subprocess mutation or verification bypass. UnityPy memoryviews become bytes at the ctypes boundary.

Selected Balanced/Small re-encode normalized audio with real libvorbis (compression levels0.6/0.8), decode it back to normalized PCM and require unchanged duration before existing bundle/PCM validation. Cache identity includes quality; source ZIP and original score identity stay untouched. Synthetic V4/full-bundle/cache tests and production Java preparation/confirmed-install bridges verify the option reaches Python. Real25c63 bundle sizes: Original8,111,012B, Balanced2,873,367B, Small2,195,585B; including menu files10,497,506 /5,259,861 /4,582,079B. No universal size/bitrate cap or end-to-end speed promise.

Name/ID selector, indexed cover cache, quality UI, map download-size labels and springy shared/dialog buttons still need installed-device visual testing. Read-only BeatSaver HEAD requests may be refused; local ZIP sizes and fake HTTPS header/bounds/redirect/body-read refusal tests pass. All console mutation tests forbid sockets. Compressed PS4 playback/timing and new management operations are NOT hardware-proven. No game assets/songs/private fixtures ship in archives.


0.1.5 retains local V2/V3/V4 preparation and adds explicit existing OrBeats library checks/confirmed one-song installation. It reuses the pinned upstream installer/transaction/score modules, auto-reads one verified installed template, retains older entries and publishes the index last. 0.1.8 additionally reuses four pinned upstream management/release/config modules for explicitly confirmed official main/Extras deployment and PS4 song removal. No server, batch queue, automatic recovery or legacy migration. The accepted0.1.2 browsing design/library/key and immutable archives are preserved. Development tests never connect to a real console.

## 0.1.5 installer proof

The same `runtime_apk_check.py --song-template ...` additionally runs `tests/console_library_probe.py` against the actual APK's Python modules and production Java status/install bridges. Socket creation is forbidden: FTP is an in-memory protocol simulation. It verifies V2/V3/V4 installation, automatic template from existing entries, empty initialized library retained/local template, prior descriptors/files unchanged, original V4 score hash, duplicate no-op, index-last publication, persistent recovery journals and refusal/rollback for live title, wrong ELF, missing/corrupt index, existing lock/recovery, stale confirmation, bad source hash, missing template, stage readback and manifest rename failure. These are NOT live networking, installed Activity or hardware playback results. Read root README/UI-CHECKLIST before the first real user-confirmed install.

## 0.1.4 production song proof

`python development/conversion/runtime_apk_check.py --song-template /private/path/to/own-compatible.bundle` exercises the actual signed APK through official AndroidPlatform/JNI with a simulated developer Application. A fixture/template and downloaded music are NEVER bundled. Synthetic V2 mono48kHz WAV, V3 stereo44100 Vorbis and advanced native V4 FLAC/AudioData/arcs/chains/NJS fixtures each pass with/without a template; the production Java preparation bridge repeats all six. Assertions cover full SerializedFile/PCM/media output reopening/validation, note counts, V4 preservation, cache reuse/repair, hash mismatch refusal, ObjectReader shallow-copy/missing-attribute regression and template positive/negative validation.

Set `ORBEATS_SONG_PROBE_REAL=/private/map.json` optionally for `{id,archive,hash,zip_sha256}`; tested real downloaded V4 BeatSaver55710 passes with/without template (153.2852380952381seconds,136ExpertPlus notes). Metadata validation was NOT relaxed to make other maps pass:556de/55719 `_suggestions`,55718 negative event beat and5570a invalid RGBA were refused under the pinned upstream rules. API mod flags are not a complete compatibility check.

Production SoundFile/libsoxr streams decode/resample to stereo PCM16/44100, adapting only the exact audited per-module ffmpeg calls. Modern decoders are privately source-built (Ogg1.3.6/Vorbis1.3.7/FLAC1.5.0/Opus1.5.2/libsndfile1.2.2), API26/16KiB, no Termux RPATH or unshipped dependencies. NumPy1.26.2/SoundFile0.13.1/CFFI1.17.1/libsoxr0.4.0 are actual native/Python dependencies, not stubs. All21 OrBeats modules remain byte-unmodified; the pinned upstream FNV C source is compiled for API26/ARM64/16KiB and its native backend is asserted in the actual APK; only explicit SoundFile Android loader and UnityPy1.20.26 ObjectReader copy compatibility patches are applied to dependencies. See root README, pins/notices/patch files and tools/build_audio.py.

The13 host SongLoader tests cover ZIP/path/duplicate/symlink/Info limits, command allowlist, cancellation/hash gates and UnityFS template bounds/expansion/truncation. They do not execute native codecs. Native APK tests are **not installed Activity/SAF/audio playback or console tests**. Full output remains an offline candidate (`runtime_ready:false`), PCM-only. Local preparation/preview/export remains separate from installation. For the new explicit console test, update in place, close Beat Saber, read the existing OrBeats library, then Library -> supported song -> Install to PS4 -> review/confirm; restart game only after success. A nonempty library automatically supplies its verified template. Hardware installation/playback remains unproved.

## Historical component proofs below

The following records describe their earlier scopes and dependencies; immutable evidence is not rewritten to imply0.1.4 results.

## Pinned reference

Read-only [Wkrotik/OrBeats at 098897736e089107704ec1633daff8922087fcc8](https://github.com/Wkrotik/OrBeats/tree/098897736e089107704ec1633daff8922087fcc8), GPL-3.0:

- `orbeats/tools/hevag_encoder.py:496-509`: `read_audio_normalized` reads float32, attenuates only when peak exceeds 0.99, multiplies by 32767 and truncates to int16.
- `orbeats/tools/hevag_encoder.py:686-769`: `build_pcm16_fsb5(..., pad_to_size=0)` retains the complete audio, unlike its legacy size-limited default.
- `orbeats/development/scripts/prepare_additive_bundle.py`: legal-template Unity/type-tree edits, audio-resource replacement and validation. Production prefers compatible Vorbis, with a PCM fallback. PCM packing alone is NOT conversion of a complete song.

The tests execute actual upstream functions; no fake codec/Unity modules or replacement reference encoder are used. The upstream checkout is not modified.

## PCM-01 / PCM-02: Java audio packing and actual Android ART

`src/dev/orbeats/conversion/Pcm16Fsb.java` uses Java8/API26 methods. It accepts regular RIFF PCM16 stereo 44100 Hz WAVs of 1–600 seconds and deliberately refuses other formats/rates/channels instead of silently resampling or discarding channels.

It validates chunk bounds/counts, rate/byte-rate/block alignment, unambiguous format/data sections and whole frames. Two streaming passes use a 64 KiB buffer, matching float32 normalization/truncation and the 125-byte FSB5 PCM header. PCM is hashed on both passes to detect changes. The output must be a NEW caller-owned staging path: existing files/symlinks are not replaced and failed new outputs are removed. This is not durable/transactional publication for an installer.

Checks:

- The same 31 assertions run on both the desktop JVM and this phone's Android ART: headers, normalization, malformed/truncated/unsupported input, minimum duration, no-overwrite, symlinks and early cancellation.
- Ten generated WAV fixtures yield byte-identical complete banks against the pinned upstream Python writer: silence, quiet samples, either side of the attenuation threshold, extrema, every int16 value, stereo tones, fmt16/fmt18, odd/trailing metadata.
- The ten comparisons also execute on Android ART, rather than just compiling DEX.
- Duplicate format/data and excessive chunks are refused. A sparse 600-second WAV converts under a **desktop JVM** `-Xmx16m`; 600 seconds plus one frame is refused. Large stress files are removed. This is not an Android heap/profile measurement.
- D8 compiles the standalone harness for API26. Execution uses a separate ART process and a process-local boot-class-path argument; it does not alter device boot configuration or install an Activity/APK. Only this phone's runtime has been tested, not an Android8 device matrix.

PCM is about 10.6 MB/minute (decimal), larger than Vorbis. Generated WAVs/banks are diagnostics, not installable songs. No downloaded music or game template is involved.

## WRITER-01: real Android-target Python and existing Unity writer

A developer C launcher (`tests/android_python.c`) initializes **Android-target CPython 3.13.16**, not Termux Python or Debian/proot Python. It uses an isolated configuration, explicit search paths and disabled bytecode writes. Its native runtime comes from the official Maven Central Chaquopy target `3.13.16-0`; private download manifests record URLs/hashes. That C launcher is not a JNI/Java bridge or production launcher; the new0.1.3 bridge uses the official Chaquopy platform instead.

Unmodified **UnityPy 1.20.26** meets OrBeats' `>=1.20` requirement. The complete extracted source is compared against its verified original sdist, including the file set. UnityPy's own supported Python type-tree fallback is used when the optional Boost extension is absent; no fake extension or codec is supplied.

Actual Android checks:

- Generated type-tree strings (including Unicode), bytes and PPtr values round-trip; truncation is refused.
- Generated UnityFS v6 containers load, edit, save and reopen using `none`, `lz4`, `lzma` and `original` packing. `none` is the upstream preparation writer's packing mode.
- Real native LZ4/Brotli compress/decompress generated data.
- Pillow encodes/decodes a generated 512×512 PNG using native dependencies.
- Missing launcher arguments/script are refused.

**Important boundary:** the generated container has a resource entry, not a game's SerializedFile, MonoBehaviour schema, object table or complete song. Its 2018.4 engine tag avoids later alignment variants. Container/type-tree checks do not establish that a real Beat Saber template round-trips correctly.

### Native audio and generated-song input checks

Android NumPy **1.26.2**, SoundFile **0.13.1**, CFFI **1.17.1**, libsndfile **1.0.28** and native Vorbis/Ogg libraries execute successfully. The Android upstream PCM writer matches all ten desktop-reference/Java banks byte-for-byte. A generated stereo 44100 Hz tone encodes and decodes through actual Vorbis with matching frame count and bounded lossy error. Other codecs, arbitrary sample rates and downmix/resampling are not validated.

The real upstream `generate_probe`/`load_song` functions also run on Android: a generated 12-second input with five V3 difficulties/nine notes each validates; identity is independent of its folder; unsupported Noodle requirements are refused. This validates generated input, **not a finished Unity bundle or all V2/V3/V4 behavior**.

SoundFile's pure upstream wheel does not recognize `sys.platform == 'android'` when falling back to a native library name. The explicit one-line `patches/soundfile-0.13.1-android.patch` allows its real `libsndfile.so` fallback on Android. The checker verifies that the staged module differs from the original wheel by exactly this patch. This is an actual loader port, not a codec stub. The inspected cp310-tagged Chaquopy SoundFile artifact is NOT forced into cp313; the probe uses the official pure Python wheel plus matching Android native dependencies. SoundFile is BSD-licensed; dependency notices/licenses must be preserved when packaging.

## Re-run on this phone

```
cd /storage/emulated/0/projects/OrBeatsAndroid
python development/conversion/check.py
# Use the private REPORT path printed by that successful run:
python development/conversion/android_writer_check.py /path/to/pcm-proof-.../report.json
```

These **offline developer checks expect staged prerequisites**, do not download/install them automatically and never contact the console. Each writes a fresh private proof directory. The current APK has a bundled in-process Python runtime for its explicit generated-data check, but no server/runtime-Termux dependency. The native audio stack described here is not included in0.1.3.

PCM prerequisites: staged JDK21/D8/Android jar under `$HOME/.cache/orbeats-android-tools`; clean pinned upstream at `$HOME/.cache/beatsaber-mod-research/sources/Wkrotik_OrBeats_android_pipeline`; existing Debian proot Python3.13.5/NumPy2.2.4/libsndfile1.2.2; privately extracted SoundFile0.13.1/CFFI2.0.0/pycparser2.23 under `conversion-reference/site` with PyPI URLs/SHA256 in `packages.json`. Other compiler warnings remain errors; JDK warning categories `options`/`strictfp` are disabled for explicit Java8 float semantics.

Native writer prerequisites live under `$HOME/.cache/orbeats-android-tools/android-python`:

- Official Maven Central target `3.13.16-0` arm64-v8a and stdlib archives; `downloads.json` records verified archive hashes/URLs.
- Verified UnityPy1.20.26 PyPI sdist, unmodified; attrs26.1.0/fsspec2026.9.0 pure wheels.
- Android cp313 LZ4 4.3.3/Brotli1.1.0/Pillow11.0.0 and its freetype/libjpeg dependencies from `https://chaquo.com/pypi-13.1/`.
- Android cp313 NumPy1.26.2/CFFI1.17.1, pycparser3.12 and native OpenBLAS/libc++/Fortran/libffi/libsndfile/FLAC/Vorbis/Ogg dependencies. The manifests record the precise wheel names/hashes; the original SoundFile0.13.1 pure wheel comes from PyPI, with the recorded loader patch applied privately.

No global packages were installed. Those native C-launcher proofs are arm64 on this phone and alone do not establish installed-APK linker/lifecycle behavior or an Android API/ABI matrix. Their private RUNPATH is not shipped. For the0.1.3 diagnostic subset, `runtime-lock.json` pins official artifact/source hashes, original notices ship in the APK, all native ELF load segments pass16KiB alignment, desktop FMOD binaries are excluded and optional FreeType/font support is omitted rather than shipping its old4KiB native dependency.

## 0.1.7 aliased-cache and console catalog regressions

Real BeatSaver25c63 contains HardStandard.dat with the correct case, but an aliased Android cache root reproduced the exact false path-escape/missing-file error in the actual APK. `song_loader.unpack` now canonicalizes the extraction destination. The `console_library` helper adapter canonicalizes upstream-generated directory roots before passing them to the unchanged upstream `local_file` guard (needed for V4's source-audio path). The 17 pinned upstream modules remain byte-unmodified; path/ZIP/hash/feature guards are retained. Host tests include cache-alias extraction; the main APK harness deliberately uses an aliased Application/files/cache root for all V2/V3/V4 preparation and simulated transaction tests.

Real25c63 passes local preparation with/without a private legal template and socket-forbidden simulated installation, preserving old entries,40 historical backups and the original score hash. Duration159.6363492063492seconds;Hard223/Expert475/ExpertPlus685 notes. A separate cold-start APK probe also passed without prior song preparation. Authorized read-only FTP fetched and SHA256-verified the actual first installed template (39-song library); that private game-derived bundle/music never enters release archives. No assistant console writes occurred. The before-fix aliased-source APK probe failed with the exact `HardStandard.dat` error; the same probe passes on the final build.

Production `MainActivity.catalogSongs` tests cover39-song preferences round-trip, normalized endpoint identity, wrong host/port, invalid/missing/empty snapshots. Library now separates On PS4 from On phone and labels saved snapshot age/not-live status. Framework tests do not prove installed row rendering or lifecycle. After updating in place, test Library/refresh in both themes, then explicitly confirm a single install with Beat Saber closed; hardware playback is still unproved.

## 0.1.6 historical-backup regression

`console_library.inspect` previously treated `.backup-*` snapshots as live recovery even when the main index decoded correctly. Authorized read-only GoldHEN inspection found 39 valid current entries and 40 older BSDALIB1 backup indexes, with no live lock/rollback/stage. The guard now ignores historical backup snapshots with the already-validated main index, matching upstream's present-index behavior. It does not remove/migrate them or enable missing-index legacy fallback. Socket-forbidden actual-APK probes preserve all 40 backups through status/append/no-op/failure cases and still refuse corrupt/missing indexes, lock/rollback/stage. Generic UI error advice no longer implies all such refusals are FTP failures. Actual0.1.7 console installation/playback was later user-confirmed;0.1.8 management hardware checks remain pending.

## 0.1.3 APK runtime bridge

After `bash build.sh`, run `python development/conversion/runtime_apk_check.py`. This executes the **actual signed APK's DEX/assets/JNI** through Android `app_process`/AssetManager with a developer-supplied Application/preferences context. Official AndroidPlatform extracts its normal bootstrap assets and uses its unmodified importer; production `ConversionRuntime.check` passes twice, temporary fixtures are cleaned and early interruption is refused. No custom JNI/ZIP installer or external Python is used by the APK. The harness is NOT an installed Activity/update/lifecycle test. The Settings engine self-test control was removed at the user's request; developer checks remain.0.1.7 hardware installation/playback was subsequently user-confirmed.

The build packager verifies SHA256-pinned inputs and tests wrong-ABI/non16KiB/misaligned ELF and unsafe-member refusal. `.imy` APK entries must remain uncompressed as upstream requires. See root README for explicit private `--fetch` staging and licenses. Old evidence snapshots describe their historical scope; do not rewrite them to claim newer results.

## Historical 0.1.3 pipeline status (superseded by 0.1.4 section above)

| Stage | Status |
|---|---|
| BeatSaver browse/download and ZIP/CRC bounds | Accepted0.1.2 behavior retained in0.1.3; archive safety is not map compatibility |
| Chart/input validation | Generated V3 input validated by unmodified upstream on Android; full V2/V3/V4 coverage pending |
| Audio decoding | Generated Vorbis stereo44100 decode passed; other rates/codecs/downmix/resampling pending |
| PCM normalization/FSB | JVM, actual ART and Android native-Python parity; not in the APK |
| Preferred compressed Vorbis bank | Not implemented/proved; decoding an OGG does not construct this bank |
| Unity writer/runtime | Generated checks pass in actual APK DEX/assets/JNI with simulated developer Application context; installed UI and real-template SerializedFile edits pending |
| Cover/preview/manifests | Generated PNG passed; full presentation output, hashes and manifest validation pending |
| Complete one-song output | NOT achieved; needs an own legally obtained template and full validators |
| Console installer | Out of scope now; zero PS4 writes |

Do not pass a PCM bank as upstream `compressed_fsb` to bypass dependencies: that argument also selects the compressed AudioClip metadata. Preserve the reference codec contract.

**Current next gate (0.1.9):** test installed quality/selector/covers/size/motion and compressed playback/timing; then separately test newly confirmed removal/plugin controls on hardware; developer tests use only simulated FTP. The full management APK harness additionally requires `ORBEATS_PLUGIN_PROBE_RELEASE` pointing to a private JSON `{manifest,prefix,root}` fixture with verified official release artifacts (never APK assets). Preserve strict upstream HTTPS/size/hash/FSELF/version validation. Also test installed-device controls and explicit real-console read/check/one-song installation/playback, keeping older songs intact. Nonempty console libraries now supply one verified template internally to the guarded installer; this is not a general game-asset dumper/exporter. Empty initialized libraries still need a retained/local legal template. No game templates are distributed here. Keep local preview/export regression checks, broaden valid-map/device coverage, preserve the accepted UI and never revive the stopped native experiment.

`evidence/PCM-01` is the immutable earlier host/DEX-only snapshot. Later `PCM-02` and `WRITER-01` snapshots record the new runtime results without rewriting that history. Snapshots contain developer evidence/source, not an app update or an installable song.
