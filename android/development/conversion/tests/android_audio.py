#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generated-data checks of real Android audio libraries and upstream PCM writer."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import shutil

import numpy as np
import soundfile as sf

assert sys.platform == 'android' and np.__version__ == '1.26.2' and sf.__version__ == '0.13.1'
upstream = Path(os.environ['ORBEATS_UPSTREAM'])
sys.path.insert(0, str(upstream/'orbeats/tools'))
from hevag_encoder import build_pcm16_fsb5

work = Path(os.environ['ORBEATS_PCM_REPORT']).parent
reference = json.loads((work/'report.json').read_text())
results = []
for case in reference['cases']:
    name = case['fixture']
    assert name == Path(name).name
    output = build_pcm16_fsb5(io.BytesIO((work/'input'/name).read_bytes()), pad_to_size=0)
    digest = hashlib.sha256(output).hexdigest()
    assert digest == case['sha256'], 'Android upstream PCM mismatch: '+name
    results.append({'fixture': name, 'sha256': digest})

# No downloaded music: encode/decode the generated stereo tone with native Vorbis.
samples, rate = sf.read(work/'input/stereo_tone.wav', dtype='float32', always_2d=True)
ogg = io.BytesIO()
sf.write(ogg, samples, rate, format='OGG', subtype='VORBIS')
assert ogg.getvalue().startswith(b'OggS')
decoded, decoded_rate = sf.read(io.BytesIO(ogg.getvalue()), dtype='float32', always_2d=True)
assert decoded_rate == 44100 and decoded.shape == samples.shape
error = float(np.abs(decoded-samples).mean())
assert error < .02 and float(np.abs(decoded).max()) > .1
# Run the real preparation module's generated-song parser/validators on Android.
spec = importlib.util.spec_from_file_location('orbeats_prepare_probe', upstream/'orbeats/development/scripts/prepare_additive_bundle.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
folder = Path(os.environ['ORBEATS_AUDIO_REPORT']).parent/'generated-song'
prepare.generate_probe(folder)
song = prepare.load_song(folder)
assert len(song['maps']) == 5 and song['samples'] == 12*44100
assert all(len(chart['colorNotes']) == 9 for chart in song['maps'].values())
copy = folder.with_name('generated-song-copy')
shutil.copytree(folder, copy)
assert prepare.load_song(copy)['source_sha256'] == song['source_sha256']
info_file = copy/'Info.dat'
info = json.loads(info_file.read_text())
info['_customData'] = {'_requirements': ['Noodle Extensions']}
info_file.write_text(json.dumps(info))
try:
    prepare.load_song(copy)
except ValueError:
    pass
else:
    raise AssertionError('Unsupported map requirements were accepted')

report = {'python': sys.version, 'platform': sys.platform, 'numpy': np.__version__,
          'soundfile': sf.__version__, 'libsndfile': sf.__libsndfile_version__,
          'upstream_pcm_matches': results, 'generated_vorbis_encode_decode': True,
          'vorbis_frames': len(decoded), 'vorbis_mean_absolute_error': error,
          'soundfile_loader_patch': 'patches/soundfile-0.13.1-android.patch',
          'generated_song': {'validated': True, 'v3_difficulties': 5, 'notes_per_difficulty': 9,
                             'path_independent_identity': True, 'unsupported_requirements_refused': True,
                             'source_sha256': song['source_sha256'], 'bundle_written': False},
          'not_tested': ['other audio formats', 'resampling/downmixing', 'installed APK', 'PS4 playback']}
Path(os.environ['ORBEATS_AUDIO_REPORT']).write_text(json.dumps(report, indent=2)+'\n')
print('PASS: Android native NumPy/SoundFile/PCM upstream parity and generated Vorbis encode/decode')
