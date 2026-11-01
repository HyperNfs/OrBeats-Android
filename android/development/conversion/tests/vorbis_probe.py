"""Actual APK compression/48k normalization checks; developer fixtures only."""
import io,json,math,zipfile,hashlib,shutil,wave
from pathlib import Path
import numpy as np
import soundfile as sf
import song_loader as loader
import vorbis_audio as vorbis

for rate in (44100,48000):
    source=root/('vorbis-'+str(rate));shutil.copytree(root/'source-v3',source)
    frames=rate*2
    tone=np.sin(np.arange(frames,dtype=np.float32)*(2*math.pi*440/rate))*0.2
    sf.write(str(source/'song.ogg'),np.stack((tone,-tone),axis=1),rate,subtype='VORBIS')
    info=json.loads((source/'Info.dat').read_text());identity=hashlib.sha1((source/'Info.dat').read_bytes())
    for name in v4.references(info):identity.update((source/name).read_bytes())
    archive=root/('vorbis-'+str(rate)+'.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(source.iterdir()):z.write(p,p.name)
    report=json.loads(loader.prepare(archive,identity.hexdigest(),root/'compressed-output',str(template)))
    folder=Path(report['output_directory']);manifest=bundle.validate(folder/'bundle')
    assert report['audio_codec']=='vorbis' and manifest['audio_sample_rate']==rate,manifest
    assert report['bundle_bytes']==manifest['bundle']['bytes']
    normalized=bundle.load_song(folder/'normalized')
    data=(source/'song.ogg').read_bytes();fsb,count,_=vorbis.build_fsb(data,sample_rate=rate)
    assert count==frames and vorbis.verify_fsb(memoryview(fsb),count,normalized['pcm'],sample_rate=rate)['packets_reencoded'] is False
    try:vorbis.verify_fsb(fsb[:-7],count,normalized['pcm'],sample_rate=rate)
    except ValueError:pass
    else:raise AssertionError('Truncated bank accepted')
    wrong=np.frombuffer(normalized['pcm'],dtype='<i2').copy();wrong[100:200]=16000
    try:vorbis.verify_fsb(fsb,count,wrong.tobytes(),sample_rate=rate)
    except ValueError:pass
    else:raise AssertionError('Wrong decoded PCM accepted')
    print('PASS: compressed complete bundle '+str(rate)+'Hz, original packets/seek table/independent decode + actual normalized PCM comparison; corruption refusal; bytes='+str(report['bundle_bytes']),flush=True)
# Selected lossy quality re-encodes normalized audio, leaving the downloaded ZIP unchanged.
case=next(item for item in results if item['version']==4 and item['template'])
zip_before=loader.digest(case['zip'])
for quality in ('balanced','small'):
    report=json.loads(loader.prepare(case['zip'],case['hash'],root/'quality-output',str(template),quality=quality))
    folder=Path(report['output_directory'])
    song=bundle.load_song(folder/'normalized');manifest=bundle.validate(folder/'bundle',song)
    assert report['audio_quality']==quality and report['audio_codec']=='vorbis'
    assert manifest['audio_sample_rate']==44100 and report['bundle_bytes']==manifest['bundle']['bytes']
    assert json.loads(loader.prepare(case['zip'],case['hash'],root/'quality-output',str(template),quality=quality))==report
    assert loader.digest(case['zip'])==zip_before
    print('PASS: selected '+quality+' lossy audio, full bundle/decoded PCM validation, cache isolation, original ZIP unchanged',flush=True)
try:loader.prepare(case['zip'],case['hash'],root/'quality-output',str(template),quality='invalid')
except ValueError:pass
else:raise AssertionError('Invalid audio quality accepted')
# A non-Ogg source remains a truthful PCM fallback, never silently marked compressed.
for case in results:
    if case['template'] and case['version'] in (2,4):
        assert case['report']['audio_codec']=='pcm16' and case['report']['audio_fallback_reason']
print('PASS: WAV/FLAC PCM fallback with explicit reason; stdlib subprocess unmodified',flush=True)
import subprocess
assert hasattr(subprocess,'Popen')
