#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Developer-only: execute the actual pinned upstream module, without stubs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import numpy
import soundfile

path = Path('/upstream/orbeats/tools/hevag_encoder.py')
spec = importlib.util.spec_from_file_location('orbeats_pcm_reference', path)
encoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encoder)
results = []
for wav in sorted(Path('/work/input').glob('*.wav')):
    bank = encoder.build_pcm16_fsb5(str(wav), pad_to_size=0)
    (Path('/work/reference') / (wav.stem + '.fsb')).write_bytes(bank)
    results.append({'fixture': wav.name, 'bytes': len(bank), 'sha256': hashlib.sha256(bank).hexdigest()})
Path('/work/reference.json').write_text(json.dumps({
    'python': platform.python_version(), 'numpy': numpy.__version__,
    'soundfile': soundfile.__version__, 'libsndfile': soundfile.__libsndfile_version__,
    'upstream_file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'cases': results,
}, indent=2) + '\n')
print('PASS: unmodified upstream PCM writer generated', len(results), 'reference banks')
