#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generated-data checks of unmodified UnityPy on Android Python, NOT a song."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys

import brotli
import lz4.block
from PIL import Image
import UnityPy
from UnityPy.files import BundleFile
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.TypeTreeNode import TypeTreeNode
from UnityPy.streams import EndianBinaryReader, EndianBinaryWriter

assert sys.platform == 'android' and sys.version_info[:2] == (3, 13)
assert UnityPy.__version__ == '1.20.26'
assert TypeTreeHelper.read_typetree_boost is None  # Library's own supported Python fallback.

# No game layout/assets: a generated tree exercises strings, binary data and PPtrs.
def node(kind, name, size=-1, children=()):
    return TypeTreeNode(m_Level=0, m_Type=kind, m_Name=name, m_ByteSize=size,
                        m_Version=1, m_Children=list(children))

root = node('GeneratedProof', 'Base', children=[
    node('string', 'm_Name'), node('string', 'm_Text'),
    node('TypelessData', 'm_Data'),
    node('PPtr<AudioClip>', 'm_Clip', children=[node('int', 'm_FileID', 4), node('SInt64', 'm_PathID', 8)]),
])
original = {'m_Name': 'Generated proof — 音楽', 'm_Text': 'rights-clean fixture\n'*16000,
            'm_Data': b'\x00\x01\xff' + gzip.compress(b'{"generated":true}', mtime=0),
            'm_Clip': {'m_FileID': 0, 'm_PathID': 123456789012}}
writer = EndianBinaryWriter(endian='<')
TypeTreeHelper.write_typetree(original, root, writer)
payload = writer.bytes

def read_tree(data):
    return TypeTreeHelper.read_typetree(root, EndianBinaryReader(data, endian='<'), byte_size=len(data))

assert read_tree(payload) == original
try:
    read_tree(payload[:-1])
except (ValueError, struct.error, EOFError):
    pass
else:
    raise AssertionError('Truncated typetree accepted')

# Minimal UnityFS v6 generated container, no SerializedFile or game template.
# 2018 engine tag deliberately avoids the later header-alignment variants.
name = 'generated.resS'
info = (bytes(16) + struct.pack('>I', 1) + struct.pack('>IIH', len(payload), len(payload), 0)
        + struct.pack('>IqqI', 1, 0, len(payload), 0) + name.encode() + b'\0')
prefix = b'UnityFS\0' + struct.pack('>I', 6) + b'5.x.x\0' + b'2018.4.36f1\0'
size = len(prefix) + 20 + len(info) + len(payload)
fixture = prefix + struct.pack('>QIII', size, len(info), len(info), 64) + info + payload

def load(blob):
    env = UnityPy.load(blob)
    assert len(env.files) == 1
    bundle = next(iter(env.files.values()))
    assert isinstance(bundle, BundleFile) and list(bundle.files) == [name]
    return bundle

bundle = load(fixture)
assert bundle.files[name].bytes == payload
changed = dict(original, m_Name='Changed only generated data', m_Clip={'m_FileID': 0, 'm_PathID': 999})
writer = EndianBinaryWriter(endian='<')
TypeTreeHelper.write_typetree(changed, root, writer)
entry = EndianBinaryReader(writer.bytes)
entry.flags = bundle.files[name].flags
bundle.files[name] = entry
results = []
for packer in ['none', 'lz4', 'lzma', 'original']:
    output = bundle.save(packer=packer)
    reopened = load(output)
    assert read_tree(reopened.files[name].bytes) == changed
    results.append({'packer': packer, 'bytes': len(output), 'sha256': hashlib.sha256(output).hexdigest()})

# Exercise actual native dependencies, not import-only or placeholder codecs.
assert brotli.decompress(brotli.compress(payload)) == payload
assert lz4.block.decompress(lz4.block.compress(payload)) == payload
image = Image.new('RGB', (16, 16), (20, 60, 30)).resize((512, 512))
png = io.BytesIO(); image.save(png, format='PNG')
with Image.open(io.BytesIO(png.getvalue())) as decoded:
    decoded.load()
    assert decoded.size == (512, 512) and decoded.getpixel((0, 0)) == (20, 60, 30)

report = {'python': sys.version, 'platform': sys.platform, 'unitypy': UnityPy.__version__,
          'typetree_python_fallback': True, 'typetree_roundtrip_and_truncation_checks': True,
          'generated_unityfs_roundtrips': results, 'native_lz4_brotli_roundtrip': True,
          'native_pillow_png_512_roundtrip': True,
          'not_tested': ['installed APK/Java bridge', 'real template SerializedFile edits',
                         'complete OrBeats conversion', 'audio resampling/other codecs', 'PS4 playback']}
Path(os.environ['ORBEATS_WRITER_REPORT']).write_text(json.dumps(report, indent=2)+'\n')
print('PASS: Android-target CPython/UnityPy; generated typetree and UnityFS none/lz4/lzma/original; native codecs/PNG')
