"""Actual APK Python tests: synthetic V2/V3/V4 inputs + private local template.
This developer script and the template are NEVER packaged in the APK.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import wave
import zipfile
print('Song probe: importing native audio',flush=True)
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
print('Song probe: NumPy loaded',flush=True)
import soundfile as sf
assert sf.__libsndfile_version__=='1.2.2',sf.__libsndfile_version__
print('Song probe: SoundFile loaded; modern libsndfile1.2.2',flush=True)
from PIL import Image
import song_loader as loader

root=Path(os.environ['ORBEATS_SONG_PROBE_ROOT']);root.mkdir()
template=Path(os.environ['ORBEATS_SONG_PROBE_TEMPLATE'])
print('Song probe: validating private template bounds',flush=True)
loader.validate_template(template,lambda:None)
print('Song probe: loading upstream modules',flush=True)
importer,v4,bundle,media=loader.pipeline()
import copy
from types import SimpleNamespace
from UnityPy.files.ObjectReader import ObjectReader
original=ObjectReader.__new__(ObjectReader);original.reader=SimpleNamespace(Position=3)
cloned=copy.copy(original)
assert cloned is not original and cloned.reader is original.reader and cloned.Position==3
assert not hasattr(ObjectReader.__new__(ObjectReader),'missing') and not hasattr(original,'missing')
print('PASS: ObjectReader copy and missing-attribute regression',flush=True)
print('Song probe: cancellation bridge',flush=True)
loader.cancelled()
print('Song probe: importing libsoxr',flush=True)
import soxr
print('Song probe: libsoxr loaded',flush=True)
results=[]
for version in (2,3,4):
    source=root/('source-v'+str(version));source.mkdir()
    rate=48000 if version==2 else 44100
    frames=96240 if version==2 else rate*2
    channels=1 if version==2 else 2
    tone=(np.sin(np.arange(frames,dtype=np.float32)*(2*math.pi*440/rate))*0.2).astype(np.float32)
    if channels==2:tone=np.stack((tone,-tone),axis=1)
    audio='song.wav' if version==2 else ('song.ogg' if version==3 else 'song.flac')
    sf.write(str(source/audio),tone,rate,subtype='PCM_16' if version==2 else ('VORBIS' if version==3 else 'PCM_16'))
    Image.new('RGB',(32,32),'#235c34').save(source/'cover.png')
    if version==4:
        info={'version':'4.0.1','song':{'title':'Android V4 Synthetic','author':'Fixture'},
              'audio':{'songFilename':audio,'audioDataFilename':'AudioData.dat','bpm':60,'previewStartTime':0.25,'previewDuration':1},
              'coverImageFilename':'cover.png','difficultyBeatmaps':[{'characteristic':'Standard','difficulty':'ExpertPlus','beatmapAuthors':{'mappers':['Synthetic']},'beatmapDataFilename':'ExpertPlus.dat','lightshowDataFilename':'Lightshow.dat','noteJumpMovementSpeed':12,'noteJumpStartBeatOffset':0}], 'customData':{'editors':{}}}
        chart={'version':'4.1.0','colorNotes':[{'b':0.25,'i':1},{'b':1}], 'colorNotesData':[{'x':2,'c':1,'d':3},{'x':1}], 'bombNotes':[{'b':0.5}], 'bombNotesData':[{'x':3,'y':2}], 'obstacles':[{'b':0.75}], 'obstaclesData':[{'x':0,'d':0.25,'w':1,'h':5}]}
        chart.update(arcs=[{'hb':0.25,'tb':1,'hi':1,'ti':1}],arcsData=[{'m':1,'tm':1}],chains=[{'hb':0.25,'tb':1,'i':1}],chainsData=[{'tx':2,'ty':1,'c':4,'s':1}],njsEvents=[{'b':0},{'b':1,'i':1}],njsEventData=[{'d':2},{'d':4,'e':4}])
        (source/'AudioData.dat').write_text(json.dumps({'version':'4.0.0','songSampleCount':frames,'songFrequency':rate,'bpmData':[{'si':0,'ei':frames,'sb':0,'eb':2}],'lufsData':[]}))
        (source/'Lightshow.dat').write_text(json.dumps({'version':'4.0.0','basicEvents':[],'basicEventTypesWithKeywords':{'d':[]}}))
    else:
        info={'_version':'2.1.0','_songName':'Android V'+str(version)+' Synthetic','_songSubName':'','_songAuthorName':'Fixture','_levelAuthorName':'Synthetic','_beatsPerMinute':120,'_songTimeOffset':0,'_shuffle':0,'_shufflePeriod':0.5,'_previewStartTime':0.25,'_previewDuration':1,'_songFilename':audio,'_coverImageFilename':'cover.png','_environmentName':'DefaultEnvironment','_allDirectionsEnvironmentName':'GlassDesertEnvironment','_difficultyBeatmapSets':[{'_beatmapCharacteristicName':'Standard','_difficultyBeatmaps':[{'_difficulty':'ExpertPlus','_difficultyRank':9,'_beatmapFilename':'ExpertPlus.dat','_noteJumpMovementSpeed':12,'_noteJumpStartBeatOffset':0}]}]}
        if version==2:chart={'_version':'2.2.0','_notes':[{'_time':0.5,'_lineIndex':1,'_lineLayer':1,'_type':0,'_cutDirection':1},{'_time':1.5,'_lineIndex':2,'_lineLayer':0,'_type':1,'_cutDirection':0}],'_obstacles':[],'_events':[]}
        else:chart={'version':'3.3.0','colorNotes':[{'b':0.5,'x':1,'y':1,'c':0,'d':1,'a':0},{'b':1.5,'x':2,'y':0,'c':1,'d':0,'a':0}],'bombNotes':[],'obstacles':[],'basicBeatmapEvents':[],'bpmEvents':[],'sliders':[],'burstSliders':[],'colorBoostBeatmapEvents':[],'lightColorEventBoxGroups':[],'lightRotationEventBoxGroups':[]}
    (source/'ExpertPlus.dat').write_text(json.dumps(chart))
    (source/'Info.dat').write_text(json.dumps(info))
    hash=hashlib.sha1((source/'Info.dat').read_bytes())
    for name in v4.references(info):hash.update((source/name).read_bytes())
    archive=root/('v'+str(version)+'.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for file in sorted(source.iterdir()):z.write(file,'map/'+file.name)
    for full in (False,True):
        print('Song probe: V'+str(version)+' template='+str(full),flush=True)
        report=json.loads(loader.prepare(archive,hash.hexdigest(),root/'output',str(template) if full else ''))
        assert report['bundle_created']==full and report['deployed'] is False
        assert sum(report['note_counts'].values())==(5 if version==4 else 2),report
        output=Path(report['output_directory'])
        assert (output/'media/song-cover.png').is_file()
        with wave.open(str(output/'media/preview.wav')) as w:assert w.getnframes()==44100 and w.getframerate()==44100 and w.getnchannels()==2
        if full:
            manifest=bundle.validate(output/'bundle')
            if version==4:assert manifest.get('native_v4'),manifest
        again=json.loads(loader.prepare(archive,hash.hexdigest(),root/'output',str(template) if full else ''))
        assert again==report
        with zipfile.ZipFile(output/'prepared-song.zip') as z:
            assert z.testzip() is None
            assert 'media/preview.wav' in z.namelist()
            assert not any(n.endswith('.py') or 'template' in n for n in z.namelist())
        results.append({'version':version,'template':full,'report':report,'zip':str(archive),'hash':hash.hexdigest()})
    # A changed cache must be rebuilt, never reported as a successful stale load.
    preview=Path(results[-1]['report']['preview']);preview.write_bytes(b'corrupt')
    rebuilt=json.loads(loader.prepare(archive,hash.hexdigest(),root/'output',str(template)))
    assert hashlib.sha256(preview.read_bytes()).hexdigest()==rebuilt['cache_files']['media/preview.wav']
    try:loader.prepare(archive,'0'*40,root/'wrong-hash')
    except ValueError as e:assert 'hash mismatch' in str(e)
    else:raise AssertionError('Wrong BeatSaver hash accepted')
    assert not list((root/'wrong-hash').glob('.loading-*'))
    print('PASS: actual APK V'+str(version)+' decode/resample/import/media, optional full SerializedFile/PCM bundle validation, cache reuse/repair and content-hash refusal',flush=True)
if os.environ.get('ORBEATS_SONG_PROBE_REAL'):
    real=json.loads(Path(os.environ['ORBEATS_SONG_PROBE_REAL']).read_text())
    assert loader.digest(real['archive'])==real['zip_sha256']
    for full in (False,True):
        print('Song probe: real BeatSaver '+real['id']+' template='+str(full),flush=True)
        report=json.loads(loader.prepare(real['archive'],real['hash'],root/'real-output',str(template) if full else ''))
        assert report['bundle_created']==full and sum(report['note_counts'].values())>0
        if full:bundle.validate(Path(report['output_directory'])/'bundle')
        print('PASS: real BeatSaver '+real['id']+' local preparation; template='+str(full)+'; duration='+str(report['duration_seconds'])+'; notes='+str(report['note_counts']),flush=True)
import runpy
runpy.run_path(str(Path(__file__).with_name('vorbis_probe.py')),init_globals={'root':root,'template':template,'bundle':bundle,'v4':v4,'results':results})
(root/'results.json').write_text(json.dumps(results,indent=2))
print('PASS: six synthetic preparations; V2/V3/V4, WAV/OGG/FLAC, stereo/mono48kHz, private-template roundtrips. NOT PS4 playback or installed-Activity testing.',flush=True)
