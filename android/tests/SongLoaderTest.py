#!/usr/bin/env python3
"""Host boundary tests. Real Android audio/full V2/V3/V4 runs are separate."""
import io
import json
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from song_loader import AudioAdapter, unpack, validate_template, prepare

class Boundaries(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def zip(self, entries):
        path=self.root/'map.zip'
        with zipfile.ZipFile(path,'w') as z:
            for name,data in entries:z.writestr(name,data)
        return path
    def test_nested_info(self):
        archive=self.zip([('folder/INFO.DAT','{}'),('folder/chart.dat','{}')])
        root,info=unpack(archive,self.root/'source')
        self.assertEqual(root.name,'folder');self.assertEqual(json.loads(info.read_text()),{})
    def test_cache_alias(self):
        real=self.root/'real';real.mkdir()
        alias=self.root/'cache-alias';alias.symlink_to(real,target_is_directory=True)
        root,info=unpack(self.zip([('Info.dat','{}'),('HardStandard.dat','{}')]),alias/'source')
        self.assertEqual(root,(real/'source').resolve())
        self.assertEqual(info,root/'Info.dat')
        self.assertTrue((root/'HardStandard.dat').resolve().is_relative_to(root))
    def test_unsafe_paths(self):
        for name in ['../escape','/absolute','dir\\escape','x:y','bad\nname']:
            with self.subTest(name=name):
                archive=self.zip([('Info.dat','{}'),(name,'x')])
                with self.assertRaises(ValueError):unpack(archive,self.root/'source')
    def test_case_duplicate(self):
        archive=self.zip([('Info.dat','{}'),('info.DAT','{}')])
        with self.assertRaises(ValueError):unpack(archive,self.root/'source')
    def test_symlink(self):
        entry=zipfile.ZipInfo('link');entry.external_attr=(stat.S_IFLNK|0o777)<<16
        archive=self.zip([('Info.dat','{}'),(entry,'../escape')])
        with self.assertRaises(ValueError):unpack(archive,self.root/'source')
    def test_info_bounds(self):
        for entries in [[('other.dat','{}')],[('Info.dat','{}'),('nested/Info.dat','{}')],[('Info.dat','x'*(2*1024*1024+1))]]:
            with self.subTest(size=len(entries)):
                with tempfile.TemporaryDirectory(dir=self.root) as target:
                    with self.assertRaises(ValueError):unpack(self.zip(entries),Path(target))
    def test_cancel(self):
        def stop():raise InterruptedError('Cancelled')
        with self.assertRaises(InterruptedError):unpack(self.zip([('Info.dat','{}')]),self.root/'source',stop)
    def test_missing_hash(self):
        with self.assertRaises(ValueError):prepare(self.root/'missing.zip','',self.root/'output',check=lambda:None)
    def test_invalid_quality(self):
        with self.assertRaises(ValueError):prepare(self.root/'missing.zip','a'*40,self.root/'output',quality='invalid',check=lambda:None)

    def test_command_allowlist(self):
        class Adapter(AudioAdapter):
            def decode(self,source,target,trim=None):self.result=(str(source),str(target),trim)
        adapter=Adapter(lambda:None)
        prefix=['ffmpeg','-nostdin','-v','error','-i','song.ogg']
        normal=prefix+['-vn','-ac','2','-ar','44100','-c:a','pcm_s16le','song.wav']
        adapter.run(normal,check=True,timeout=120);self.assertEqual(adapter.result,('song.ogg','song.wav',None))
        preview=prefix+['-map','0:a:0','-vn','-af','aresample=44100,atrim=start_sample=44100:end_sample=88200,asetpts=PTS-STARTPTS','-ar','44100','-ac','2','-c:a','pcm_s16le','preview.wav']
        adapter.run(preview,check=True);self.assertEqual(adapter.result[2],(44100,88200))
        for args,kwargs in [(['sh','-c','evil'],{'check':True}),(normal,{}),(normal[:-2]+['float32','out.wav'],{'check':True}),(preview[:10]+['arbitrary_filter']+preview[11:],{'check':True})]:
            with self.assertRaises(ValueError):adapter.run(args,**kwargs)
    def template(self, expanded=4, mode=0):
        payload=b'data';table=bytes(16)+struct.pack('>iIIHiqqI',1,expanded,len(payload),mode,1,0,4,0)+b'entry\0'
        header=b'UnityFS\0'+struct.pack('>I',6)+b'5.x.x\0'+b'2019.1.0f1\0'
        size=len(header)+20+len(table)+len(payload)
        raw=header+struct.pack('>qIII',size,len(table),len(table),0x40)+table+payload
        path=self.root/'template.bundle';path.write_bytes(raw);return path
    def test_valid_template_bounds(self):validate_template(self.template(),lambda:None)
    def test_expansion_limit(self):
        with self.assertRaises(ValueError):validate_template(self.template(33*1024*1024),lambda:None)
    def test_unsupported_template_codec(self):
        with self.assertRaises(ValueError):validate_template(self.template(mode=4),lambda:None)
    def test_truncated_template(self):
        path=self.template();path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaises(ValueError):validate_template(path,lambda:None)

if __name__=='__main__':unittest.main()
