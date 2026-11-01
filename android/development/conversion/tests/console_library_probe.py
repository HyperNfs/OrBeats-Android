"""Exercise the APK's real pinned installer with an in-memory FTP, NEVER a socket."""
import copy
from ftplib import error_perm
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import wave

import console_library as android
import song_loader as loader

root=Path(os.environ['ORBEATS_SONG_PROBE_ROOT'])
cases=json.loads((root/'results.json').read_text())
_, core, library=android.modules()
import score_source
import console_transaction
import native_hash
assert native_hash.BACKEND == 'native', 'Packaged upstream native checksum did not load'
assert native_hash.fnv(bytes(range(256))*65536) == 887018771882058533
print('PASS: APK upstream native FNV, embedded-NUL 16MiB wire-checksum parity',flush=True)
BASE=library.BASE
plugin=b'private fake plugin fixture, not executable'
cap={'schema':1,'title':'CUSA12878','max_songs':64,'library_format':4,'native_maps':1,'active_elf_sha256':hashlib.sha256(plugin).hexdigest()}
flags={'enable_plugin':True,'enable_additive_song_packs':True}


def empty():
    return {BASE+'/library.bin':library.encode([]),BASE+'/companion-protocol.json':json.dumps(cap).encode(),
        '/data/GoldHEN/plugins/orbeats.prx':plugin,
        '/data/GoldHEN/AFR/CUSA12878/features.json':json.dumps(flags).encode()}


def seed():
    report=cases[1]['report'];out=Path(report['output_directory'])
    manifest=json.loads((out/'bundle/manifest.json').read_text())
    blobs=[(out/'bundle'/manifest['bundle']['file']).read_bytes(),(out/'media/song-cover.png').read_bytes(),(out/'media/preview.wav').read_bytes()]
    song=library.decode(library.encode([library.descriptor(manifest,*blobs,1)]))[0]
    files=empty();files[BASE+'/library.bin']=library.encode([song])
    files.update(zip(library.paths(song),blobs))
    return files,song


class FakeFTP:
    files={};dirs=set();ops=[];running=False;fail='';failed=False
    def __init__(self):pass
    def connect(self,host,port,**kwargs):
        assert host=='192.168.1.2' and port==2121
    def login(self,*args):pass
    def close(self):pass
    def nlst(self,path):
        if path=='/mnt/sandbox':return ['CUSA12878-app0'] if self.running else []
        return [p for p in set(self.files)|self.dirs if p.rsplit('/',1)[0]==path]
    def retrbinary(self,cmd,callback,*args):
        path=cmd.removeprefix('RETR ')
        if path not in self.files:raise error_perm('550 missing')
        content=self.files[path]
        if path.endswith('.prx') and content[:4]==bytes.fromhex('4f153d1d'):
            import library_manager
            content=library_manager.elf_from_fself(content)
        if self.fail=='stage-readback' and '.stage-' in path and not FakeFTP.failed:
            FakeFTP.failed=True;content=b'incorrect readback'
        if self.fail=='published-readback' and path==BASE+'/library.bin' and len(library.decode(content))>1 and not FakeFTP.failed:
            FakeFTP.failed=True;content=b'incorrect published index'
        callback(content)
    def storbinary(self,cmd,stream,*args):
        path=cmd.removeprefix('STOR ');self.ops.append(('STOR',path));self.files[path]=stream.read()
    def mkd(self,path):
        if path in self.dirs:raise error_perm('550 exists')
        self.ops.append(('MKD',path));self.dirs.add(path)
    def rmd(self,path):
        if path not in self.dirs:raise error_perm('550 missing')
        self.ops.append(('RMD',path));self.dirs.remove(path)
    def delete(self,path):
        if self.fail=='cleanup' and 'library.bin.rollback-' in path:raise error_perm('550 simulated cleanup failure')
        if path not in self.files:raise error_perm('550 missing')
        if self.fail=='cleanup-song' and path.endswith('.bundle'):raise error_perm('450 simulated song cleanup failure')
        self.ops.append(('DELE',path));del self.files[path]
    def rename(self,old,new):
        self.ops.append(('RENAME',old,new))
        if (self.fail=='publish' and new==BASE+'/library.bin' or self.fail=='publish-ini' and new=='/data/GoldHEN/plugins.ini') and '.stage-' in old and not FakeFTP.failed:
            FakeFTP.failed=True;raise OSError('simulated lost rename')
        if new in self.files:raise error_perm('550 exists')
        self.files[new]=self.files.pop(old)


def reset(files):
    FakeFTP.files=copy.deepcopy(files);FakeFTP.dirs={BASE}|{p.rsplit('/',1)[0] for p in files}
    FakeFTP.ops=[];FakeFTP.running=False;FakeFTP.fail='';FakeFTP.failed=False


def status():return json.loads(android.status('192.168.1.2',2121))


def install(case,snapshot=None,template=''):
    s=snapshot or status()
    return json.loads(android.install('192.168.1.2',2121,case['zip'],case['hash'],root/'recovery',root/'install-work',template,s['library_sha256'],s['plugin_sha256']))


def refused(action,text):
    before=FakeFTP.files.get(BASE+'/library.bin')
    try:action()
    except Exception as error:assert text.lower() in str(error).lower(),(text,str(error))
    else:raise AssertionError('Failure accepted: '+text)
    assert FakeFTP.files.get(BASE+'/library.bin')==before,'Old index not retained'


original_socket=socket.socket
original_session=android.Session
# If any test accidentally escapes FakeFTP it MUST fail before opening a socket.
socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Network forbidden in installer proof'))
android.Session=FakeFTP
try:
    files,old_song=seed()
    historical={BASE+'/library.bin.backup-'+format(i,'032x'):library.encode([]) for i in range(40)}
    files.update(historical);reset(files)
    snapshot=status();assert len(snapshot['songs'])==1 and snapshot['read_only'] and not FakeFTP.ops
    retained={p:FakeFTP.files[p] for p in library.paths(old_song)}
    indexed=snapshot['songs'][0];assert isinstance(indexed['cover_fnv'],str)
    cover_path=library.paths(old_song)[1]
    FakeFTP.running=True
    assert android.cover('192.168.1.2',2121,indexed['id'],indexed['cover_bytes'],indexed['cover_fnv'])==FakeFTP.files[cover_path]
    FakeFTP.running=False
    refused(lambda:android.cover('192.168.1.2',2121,indexed['id'],indexed['cover_bytes'],str(int(indexed['cover_fnv'])^1)),'checksum')
    refused(lambda:android.cover('192.168.1.2',2121,'../bad',indexed['cover_bytes'],indexed['cover_fnv']),'level ID')
    refused(lambda:android.cover('192.168.1.2',2121,indexed['id'],4194305,indexed['cover_fnv']),'bounds')
    assert not FakeFTP.ops
    print('PASS: read-only indexed cover fetch, unsigned FNV, wrong checksum/path/size refusal; no console writes',flush=True)
    if os.environ.get('ORBEATS_SONG_PROBE_REAL'):
        real=json.loads(Path(os.environ['ORBEATS_SONG_PROBE_REAL']).read_text())
        assert loader.digest(real['archive'])==real['zip_sha256']
        print('Installer probe: real BeatSaver '+real['id']+' FIRST, before other installs',flush=True)
        result=install({'zip':real['archive'],'hash':real['hash']})
        songs=library.decode(FakeFTP.files[BASE+'/library.bin'])
        assert result['ok'] and len(songs)==2 and songs[0]==old_song
        assert all(FakeFTP.files[p]==b for p,b in retained.items()) and all(FakeFTP.files[p]==b for p,b in historical.items())
        assert FakeFTP.files[BASE+'/'+songs[-1]['id']+'-score-source.bin']==score_source.encode(songs[-1],real['hash'])
        print('PASS: real BeatSaver '+real['id']+' simulated install; old entries/backups retained, original score hash',flush=True)
        reset(files)
    for version in (3,4):
        case=next(c for c in cases if c['version']==version and not c['template'])
        result=install(case)
        songs=library.decode(FakeFTP.files[BASE+'/library.bin'])
        assert result['ok'] and result['audio_codec']==('vorbis' if version==3 else 'pcm16') and len(songs)==version-1
        assert songs[0]==old_song and all(FakeFTP.files[p]==b for p,b in retained.items())
        assert all(FakeFTP.files[p]==b for p,b in historical.items()),'Historical backups changed'
        new=songs[-1]
        assert FakeFTP.files[BASE+'/'+new['id']+'-score-source.bin']==score_source.encode(new,case['hash'])
        for path in library.paths(new):assert path in FakeFTP.files
        assert FakeFTP.files[BASE+'/companion-protocol.json']==files[BASE+'/companion-protocol.json']
        assert FakeFTP.files['/data/GoldHEN/plugins/orbeats.prx']==plugin
        assert FakeFTP.files['/data/GoldHEN/AFR/CUSA12878/features.json']==files['/data/GoldHEN/AFR/CUSA12878/features.json']
        assert BASE+'/.install-lock' not in FakeFTP.dirs
        publish=next(i for i,o in enumerate(FakeFTP.ops) if o[0]=='RENAME' and o[2]==BASE+'/library.bin')
        assert all(i<publish for i,o in enumerate(FakeFTP.ops) if o[0]=='STOR' and not o[1].startswith(BASE+'/library.bin.stage-'))
        FakeFTP.ops=[]
        print('PASS: APK real upstream V'+str(version)+' append, template auto-read, old songs retained, original score identity, index last',flush=True)
    # Reimport is a no-op, not a duplicate or in-place repair.
    before=FakeFTP.files[BASE+'/library.bin'];result=install(case)
    assert result['already_present'] and FakeFTP.files[BASE+'/library.bin']==before
    # Every remote write stays inside the existing additive directory.
    assert all(p.startswith(BASE+'/') for op in FakeFTP.ops for p in op[1:])
    assert list((root/'recovery/transactions').rglob('journal.json'))
    assert all(FakeFTP.files[p]==b for p,b in historical.items())
    print('PASS: duplicate/no-op, confined own paths, durable local journals; 40 historical backups accepted and preserved',flush=True)
    # Empty library can use its retained template or explicit local legal one.
    sample=next(c for c in cases if c['version']==2 and not c['template'])
    for retained_template in (True,False):
        base=empty()
        if retained_template:base[BASE+'/template.bundle']=Path(os.environ['ORBEATS_SONG_PROBE_TEMPLATE']).read_bytes()
        reset(base);result=install(sample,template='' if retained_template else os.environ['ORBEATS_SONG_PROBE_TEMPLATE'])
        assert result['ok'] and result['count']==1
    print('PASS: empty initialized library with retained/local legal template',flush=True)
    reset(empty());refused(lambda:install(sample),'one-time legal conversion template')
    reset(files);FakeFTP.running=True;refused(status,'close Beat Saber');assert not FakeFTP.ops
    reset(files);FakeFTP.files['/data/GoldHEN/plugins/orbeats.prx']=b'changed';refused(status,'mismatch');assert not FakeFTP.ops
    reset(files);FakeFTP.files[BASE+'/library.bin']=b'bad';refused(status,'library');assert not FakeFTP.ops
    reset(files);del FakeFTP.files[BASE+'/library.bin'];refused(status,'No OrBeats library');assert not FakeFTP.ops
    reset(files);FakeFTP.dirs.add(BASE+'/.install-lock');refused(status,'lock');assert not FakeFTP.ops
    for marker in ('library.bin.rollback-unknown','library.bin.stage-unknown'):
        reset(files);FakeFTP.files[BASE+'/'+marker]=b'old';refused(status,'recovery');assert not FakeFTP.ops
    reset(files);saved=status();FakeFTP.files[BASE+'/library.bin']=library.encode([]);refused(lambda:install(sample,saved),'changed since confirmation');assert not FakeFTP.ops
    reset(files);bad=dict(sample,hash='0'*40);refused(lambda:install(bad),'hash mismatch');assert not FakeFTP.ops
    # Upload/readback failures never publish a partial song into the index.
    for failure in ('stage-readback','publish','published-readback'):
        reset(files);FakeFTP.fail=failure
        case=next(c for c in cases if c['version']==3 and not c['template'])
        refused(lambda:install(case),'simulated lost rename' if failure=='publish' else 'readback')
        assert FakeFTP.files[BASE+'/library.bin']==files[BASE+'/library.bin']
        assert all(FakeFTP.files[p]==b for p,b in retained.items())
        assert all(FakeFTP.files[p]==b for p,b in historical.items())
        assert BASE+'/.install-lock' not in FakeFTP.dirs
    reset(files);FakeFTP.fail='cleanup'
    try:install(case)
    except error_perm as error:assert 'cleanup failure' in str(error)
    else:raise AssertionError('Cleanup failure concealed')
    assert len(library.decode(FakeFTP.files[BASE+'/library.bin']))==2  # Already committed: never roll it back blindly.
    refused(status,'recovery')
    assert any(json.loads(p.read_text())['complete'] for p in (root/'recovery/transactions').rglob('journal.json'))
    for mutated in ({**flags,'enable_custom_song_replacements':True},{'enable_plugin':False}):
        reset(files);FakeFTP.files['/data/GoldHEN/AFR/CUSA12878/features.json']=json.dumps(mutated).encode()
        refused(status,'legacy' if mutated.get('enable_plugin') else 'not enabled');assert not FakeFTP.ops
    for mutated in ({**cap,'max_songs':True},{**cap,'library_format':5},{**cap,'title':'WRONG'}):
        reset(files);FakeFTP.files[BASE+'/companion-protocol.json']=json.dumps(mutated).encode()
        refused(status,'required' if mutated['title']=='WRONG' else 'capability');assert not FakeFTP.ops
    reset(files);limited={**cap,'max_songs':1};FakeFTP.files[BASE+'/companion-protocol.json']=json.dumps(limited).encode()
    refused(lambda:install(case),'exceed');assert not any(op[0]=='STOR' for op in FakeFTP.ops)
    reset(files);FakeFTP.files[library.paths(old_song)[0]]=b'corrupt template'
    refused(lambda:install(case),'verification failed');assert not any(op[0]=='STOR' for op in FakeFTP.ops)
    print('PASS: live game/plugin/features/capability/capacity/index/lock/recovery/snapshot/source/template refusals; stage and post-publication rollback; committed-cleanup failure retains recovery and blocks retry',flush=True)
    # Module bindings must be restored even after failed installation.
    assert core.FTP is not FakeFTP and score_source.original_hash.__name__=='original_hash'
    import runpy
    runpy.run_path(str(Path(__file__).with_name('management_probe.py')),init_globals=globals())
    # Leave only this explicit simulation installed for the Java bridge assertions.
    reset(files)
    case=next(c for c in cases if c['version']==3 and not c['template'])
    (root/'console-bridge.json').write_text(json.dumps(case))
    bridge_ready=True
finally:
    android.Session=original_session
    socket.socket=original_socket
# The caller invokes Java synchronously, then MUST call this cleanup in finally.
def restore_console_probe():
    android.Session=original_session
    socket.socket=original_socket
if globals().get('bridge_ready'):
    android.Session=FakeFTP
    socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Network forbidden in Java installer proof'))
print('PASS: actual APK installer with simulated FTP ONLY; no real console connections/writes, no hardware playback claim',flush=True)
