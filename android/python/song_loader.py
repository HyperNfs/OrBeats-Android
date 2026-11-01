"""Local Android adapter for the pinned, unmodified GPL OrBeats V2/V3/V4 preparer.

Only JSON/media are read from maps: map scripts/plugins are never imported.
The desktop subprocess boundary is replaced per-module, never globally patched.
"""
import builtins
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import sys
import tempfile
import zipfile

# The converter does not use parallel BLAS; avoid a native thread pool per app.
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')


def cancelled():
    from java import jclass
    if jclass('java.lang.Thread').currentThread().isInterrupted():
        raise InterruptedError('Song loading cancelled')


def unpack(archive, destination, check=lambda: None):
    archive, destination = Path(archive), Path(destination).resolve()
    if not 1 <= archive.stat().st_size <= 128*1024*1024:
        raise ValueError('Map ZIP exceeds128MiB')
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if len(entries) > 5000 or sum(e.file_size for e in entries) > 512*1024*1024:
            raise ValueError('Expanded map exceeds bounds')
        seen = set()
        for e in entries:
            p = PurePosixPath(e.filename)
            name = str(p).rstrip('/').casefold()
            if (not name or p.is_absolute() or '..' in p.parts or '\\' in e.filename
                    or ':' in e.filename or any(ord(c) < 32 for c in e.filename)
                    or name in seen or stat.S_ISLNK(e.external_attr >> 16) or e.flag_bits & 1):
                raise ValueError('Unsafe, encrypted or duplicate ZIP entry')
            seen.add(name)
        for e in entries:
            check()
            target = destination / e.filename
            if e.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with z.open(e) as source, target.open('xb') as output:
                while chunk := source.read(65536):
                    check(); written += len(chunk)
                    if written > e.file_size:
                        raise ValueError('ZIP size mismatch')
                    output.write(chunk)
            if written != e.file_size:
                raise ValueError('Truncated ZIP entry')
    infos = [p for p in destination.rglob('*') if p.name.casefold() == 'info.dat']
    if len(infos) != 1 or infos[0].stat().st_size > 2*1024*1024:
        raise ValueError('Expected exactly one bounded Info.dat')
    return infos[0].parent, infos[0]


class AudioAdapter:
    """Only the audited conversion/preview/verification commands, using native codecs."""
    def __init__(self, check):
        self.check = check

    def run(self, args, **kwargs):
        # The upstream48kHz verifier imports subprocess locally for this exact pipe.
        if args == ['ffmpeg','-nostdin','-v','error','-i','pipe:0','-vn','-ac','2','-ar','44100','-c:a','pcm_s16le','-f','s16le','pipe:1']:
            import wave
            from types import SimpleNamespace
            data=kwargs.get('input')
            if kwargs.get('check') is not True or not isinstance(data,bytes) or not 1<=len(data)<=200000000:
                raise ValueError('Invalid verification audio input')
            with tempfile.TemporaryDirectory(prefix='verify-audio-') as work:
                target=Path(work)/'decoded.wav'
                self.decode(io.BytesIO(data),target)
                with wave.open(str(target),'rb') as stream:
                    return SimpleNamespace(stdout=stream.readframes(stream.getnframes()))
        basic = ['-nostdin', '-v', 'error', '-i']
        if args[0] != 'ffmpeg' or args[1:5] != basic or kwargs.get('check') is not True:
            raise ValueError('Unexpected desktop decoder command')
        source, target = Path(args[5]), Path(args[-1])
        trim = None
        if args[6:-1] != ['-vn', '-ac', '2', '-ar', '44100', '-c:a', 'pcm_s16le']:
            if (len(args) != 18 or args[6:10] != ['-map', '0:a:0', '-vn', '-af']
                    or args[11:-1] != ['-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le']):
                raise ValueError('Unexpected preview decoder command')
            match = re.fullmatch(r'aresample=44100,atrim=start_sample=(\d+):end_sample=(\d+),asetpts=PTS-STARTPTS', args[10])
            if not match:
                raise ValueError('Unsupported preview trim')
            trim = tuple(map(int, match.groups()))
        self.decode(source, target, trim)

    def decode(self, source, target, trim=None):
        import numpy as np
        import soundfile as sf
        import soxr
        self.check()
        if target.exists():
            raise ValueError('Refusing to overwrite decoded audio')
        # shortcut: libsndfile supports WAV/OGG/FLAC here; add a decoder if a real map needs another codec.
        with sf.SoundFile(source if hasattr(source,'read') else str(source)) as stream:
            if stream.channels not in (1, 2) or not 8000 <= stream.samplerate <= 192000 or not 1 <= stream.frames/stream.samplerate <= 600:
                raise ValueError('Audio must be mono/stereo,1..600seconds,8..192kHz')
            rate, frames = stream.samplerate, stream.frames
            resampler = soxr.ResampleStream(rate, 44100, 2, dtype='float32', quality='HQ') if rate != 44100 else None
            expected = round(frames*44100/rate)
            start, end = trim if trim is not None else (0, expected+1)
            if not 0 <= start < end <= expected+1 or (trim is not None and not 44100 <= end-start <= 30*44100):
                raise ValueError('Preview exceeds audio bounds')
            consumed = produced = written = 0
            with sf.SoundFile(str(target), 'w', samplerate=44100, channels=2, format='WAV', subtype='PCM_16') as output:
                while consumed < frames:
                    self.check()
                    data = stream.read(min(65536, frames-consumed), dtype='float32', always_2d=True)
                    if not len(data) or not np.isfinite(data).all(): raise ValueError('Truncated or non-finite audio')
                    consumed += len(data)
                    if data.shape[1] == 1: data = np.repeat(data, 2, axis=1)
                    if resampler is not None: data = resampler.resample_chunk(data, last=consumed==frames)
                    left, right = max(0,start-produced), min(len(data),end-produced)
                    if left < right: output.write(data[left:right]); written += right-left
                    produced += len(data)
            # libsoxr rounding can differ by one sample at fractional endpoints.
            if consumed != frames or abs(produced-expected)>1 or (trim is not None and abs(written-(end-start))>1):
                raise ValueError('Decoded/resampled audio frame mismatch')
        self.check()


def audio_adapter(check):
    import vorbis_audio
    from types import FunctionType
    adapter=AudioAdapter(check)
    original=getattr(vorbis_audio,'_android_verify_original',vorbis_audio.verify_fsb)
    vorbis_audio._android_verify_original=original
    # The verifier imports its decoder locally; isolate that binding, never stdlib.
    def local_import(name,*args,**kwargs):
        return adapter if name=='subprocess' else builtins.__import__(name,*args,**kwargs)
    verify=FunctionType(original.__code__,{**original.__globals__,'__builtins__':{**vars(builtins),'__import__':local_import}},
                        original.__name__,original.__defaults__,original.__closure__)
    verify.__kwdefaults__=original.__kwdefaults__
    # UnityPy1.20 resources may be memoryviews; ctypes packet buffers require bytes.
    vorbis_audio.verify_fsb=lambda fsb,*args,**kwargs:verify(bytes(fsb),*args,**kwargs)
    return adapter


def validate_template(path, check=cancelled):
    """Bound UnityFS expansion before handing a selected local file to UnityPy."""
    path = Path(path)
    if not path.is_file() or not 1 <= path.stat().st_size <= 200000000:
        raise ValueError('Invalid conversion template (maximum200MB)')
    check()
    raw = path.read_bytes()
    stream = io.BytesIO(raw)
    def read(n):
        value = stream.read(n)
        if len(value) != n: raise ValueError('Truncated template')
        return value
    def integer(fmt):
        return struct.unpack('>'+fmt, read(struct.calcsize('>'+fmt)))[0]
    def text(limit):
        value = bytearray()
        for _ in range(limit):
            c = read(1)
            if c == b'\0': return value.decode('utf-8')
            value += c
        raise ValueError('Unbounded template string')
    if text(16) != 'UnityFS': raise ValueError('Template must be a UnityFS song bundle')
    format_version = integer('I'); text(128); engine = text(128)
    if format_version not in (6, 7, 8): raise ValueError('Unsupported UnityFS format')
    size, packed, unpacked, flags = integer('q'), integer('I'), integer('I'), integer('I')
    match = re.match(r'(\d+)\.(\d+)', engine)
    if not match: raise ValueError('Missing template Unity version')
    version = tuple(map(int, match.groups()))
    if size != len(raw) or not 1 <= packed <= 1024*1024 or not 1 <= unpacked <= 4*1024*1024 or flags & ~0x2ff or not flags & 0x40 or (version < (2020, 0) and flags & 0x200):
        raise ValueError('Unsafe template header bounds/flags')
    if format_version >= 7:
        stream.seek((stream.tell()+15)//16*16)
    elif version >= (2019, 4):
        start = stream.tell(); padding = read((-start)%16)
        if any(padding): stream.seek(start)
    start = stream.tell()
    table_offset = len(raw)-packed if flags & 0x80 else start
    if table_offset < start or table_offset+packed > len(raw): raise ValueError('Template table outside file')
    def decompress(data, expected, mode):
        check()
        mode &= 0x3f
        if mode == 0: value = data
        elif mode in (2, 3):
            import lz4.block
            value = lz4.block.decompress(data, uncompressed_size=expected)
        elif mode == 1:
            props, dictionary = struct.unpack('<BI', data[:5])
            if not 4096 <= dictionary <= 64*1024*1024: raise ValueError('Unsafe LZMA dictionary')
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{'id':lzma.FILTER_LZMA1,'dict_size':dictionary,'lc':props%9,'lp':(props//9)%5,'pb':props//45}])
            value = decoder.decompress(data[5:], max_length=expected+1)
        else: raise ValueError('Unsupported template compression/encryption')
        if len(value) != expected: raise ValueError('Template expanded size mismatch')
        return value
    table = decompress(raw[table_offset:table_offset+packed], unpacked, flags)
    stream = io.BytesIO(table); read(16); count = integer('i')
    if not 1 <= count <= 4096: raise ValueError('Unsafe template block count')
    blocks = [(integer('I'), integer('I'), integer('H')) for _ in range(count)]
    total = sum(b[0] for b in blocks)
    if not 1 <= total <= 128*1024*1024 or any(not 1 <= b[0] <= 32*1024*1024 or not 1 <= b[1] <= 64*1024*1024 for b in blocks): raise ValueError('Template expansion exceeds128MiB')
    nodes = integer('i')
    if not 1 <= nodes <= 16: raise ValueError('Too many template files')
    for _ in range(nodes):
        offset, length = integer('q'), integer('q'); integer('I'); text(512)
        if offset < 0 or length < 0 or offset+length > total: raise ValueError('Template file outside blocks')
    cursor = start if flags & 0x80 else start+packed
    if flags & 0x200: cursor = (cursor+15)//16*16
    end = table_offset if flags & 0x80 else len(raw)
    for expanded, compressed, mode in blocks:
        if cursor+compressed > end: raise ValueError('Template block outside file')
        decompress(raw[cursor:cursor+compressed], expanded, mode); cursor += compressed
    if cursor != end: raise ValueError('Unexpected trailing template data')


def pipeline():
    import orbeats_pipeline
    root = Path(orbeats_pipeline.__file__).parent
    for folder in (str(root/'tools'), str(root/'development/scripts'), str(root/'webapp')):
        if folder not in sys.path: sys.path.insert(0, folder)
    import import_v3_additive as importer
    import import_v4_additive as v4
    import prepare_additive_bundle as bundle
    import prepare_additive_media as media
    return importer, v4, bundle, media


def source_audio(source,info,bundle):
    path=bundle.local_file(source,info.get('_songFilename',info.get('audio',{}).get('songFilename')))
    if not 1<=path.stat().st_size<=200000000:raise ValueError('Original audio exceeds200MB')
    return path


AUDIO_QUALITIES={'original':None,'balanced':0.6,'small':0.8}


def quality_audio(normalized,original_audio,quality,adapter,bundle):
    if quality not in AUDIO_QUALITIES:raise ValueError('Unknown audio quality')
    if quality=='original':return original_audio
    import wave
    import soundfile as sf
    import numpy as np
    normalized=Path(normalized).resolve()
    info=json.loads(bundle.local_file(normalized,'Info.dat').read_bytes())
    audio=source_audio(normalized,info,bundle)
    encoded=normalized.parent/'.android-quality.ogg'
    with sf.SoundFile(str(audio)) as source:
        if source.samplerate!=44100 or source.channels!=2 or not 44100<=source.frames<=44100*600:
            raise ValueError('Quality encoding requires bounded normalized stereo44100 audio')
        frames=source.frames
        with sf.SoundFile(str(encoded),'w',samplerate=44100,channels=2,format='OGG',subtype='VORBIS',compression_level=AUDIO_QUALITIES[quality]) as output:
            while True:
                adapter.check();block=source.read(65536,dtype='float32',always_2d=True)
                if not len(block):break
                if not np.isfinite(block).all():raise ValueError('Non-finite audio during quality encoding')
                output.write(block)
    # Validate the selected lossy audio against its own decoded PCM, never the original waveform.
    decoded=normalized.parent/'.android-quality.wav'
    adapter.decode(encoded,decoded)
    with wave.open(str(decoded),'rb') as check:
        if abs(check.getnframes()-frames)>1:raise ValueError('Quality encoding changed audio duration')
    decoded.replace(audio)
    return encoded


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verified_source(archive, expected_hash, destination, check=cancelled):
    if not re.fullmatch('[0-9a-fA-F]{40}', expected_hash):
        raise ValueError('Missing BeatSaver content hash; download this map again')
    _, v4, bundle, _ = pipeline()
    source, info_path = unpack(archive, destination, check)
    info_bytes = info_path.read_bytes()
    info = json.loads(info_bytes)
    content_hash = hashlib.sha1(info_bytes)
    for name in v4.references(info):
        file = bundle.local_file(source, name)
        if file.stat().st_size > 32*1024*1024:
            raise ValueError('Referenced chart/AudioData exceeds32MiB')
        content_hash.update(file.read_bytes())
    if content_hash.hexdigest().lower() != expected_hash.lower():
        raise ValueError('BeatSaver content hash mismatch; download again')
    return source, info


def prepare(archive, expected_hash, output_root, template='', check=cancelled, quality='original'):
    if quality not in AUDIO_QUALITIES:raise ValueError('Unknown audio quality')
    archive, output_root = Path(archive), Path(output_root)
    if not re.fullmatch('[0-9a-fA-F]{40}', expected_hash):
        raise ValueError('Missing BeatSaver content hash; download this map again')
    if template and (not Path(template).is_file() or not 1 <= Path(template).stat().st_size <= 200000000):
        raise ValueError('Invalid conversion template (maximum200MB)')
    check()
    if template: validate_template(template, check)
    importer, v4, bundle, media = pipeline()
    identity = digest(archive)
    template_hash = digest(template) if template else ''
    key = hashlib.sha256(('android-0.1.9-quality1'+quality+identity+template_hash).encode()).hexdigest()[:32]
    # shortcut: prepared outputs use evictable app cache; add quota eviction before batch conversion.
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root/key
    if (destination/'report.json').is_file():
        try:
            cached = json.loads((destination/'report.json').read_text())
            files = cached['cache_files']
            if cached['beatsaver_hash'] != expected_hash.lower(): raise ValueError('BeatSaver hash changed')
            if not files or 'prepared-song.zip' not in files: raise ValueError('Incomplete preparation cache')
            for name, sha in files.items():
                check()
                path = PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts or digest(destination/name) != sha: raise ValueError('Preparation cache changed')
            return json.dumps(cached)
        except InterruptedError:
            raise
        except (OSError, ValueError, KeyError):
            shutil.rmtree(destination)
    elif destination.exists():
        shutil.rmtree(destination)
    adapter = audio_adapter(check)
    importer.subprocess = adapter
    importer.v2.subprocess = adapter
    media.subprocess = adapter
    with tempfile.TemporaryDirectory(prefix='.loading-', dir=output_root) as work:
        work = Path(work)
        source, info = verified_source(archive, expected_hash, work/'source', check)
        original_audio=source_audio(source,info,bundle)
        version = str(info.get('_version', info.get('version', 'unknown')))
        if not str(info.get('_version', '')).startswith('2.'):
            v4.normalize(source, work/'v4', bundle.local_file)
            source = work/'v4'
        check()
        imported = importer.import_song(source, work/'normalized')
        original_audio=quality_audio(work/'normalized',original_audio,quality,adapter,bundle)
        song = bundle.load_song(work/'normalized')
        result = work/'result'; result.mkdir()
        shutil.move(str(work/'normalized'), str(result/'normalized'))
        level = {'level_id': 'bsd_additive_'+song['source_sha256'][:24],
                 'song_name': song['title'], 'duration_seconds': song['samples']/44100}
        prepared = None
        if template:
            prepared = bundle.prepare(result/'normalized', template, result/'bundle', original_audio=original_audio)
            bundle.validate(result/'bundle', song)
            level = prepared
        (result/'level-metadata.json').write_text(json.dumps(level))
        menu = media.prepare(source, result/'level-metadata.json', result/'media')
        report = {'title': song['title'], 'info_version': version,
                  'chart_versions': {k: v.get('version', v.get('_version')) for k,v in song['maps'].items()},
                  'duration_seconds': song['samples']/44100, 'note_counts': imported['note_counts'],
                  'skipped_difficulties': imported.get('skipped_difficulties', []),
                  'source_zip_sha256': identity, 'beatsaver_hash': expected_hash.lower(),
                  'template_sha256': template_hash, 'bundle_created': prepared is not None,
                  'audio_quality':quality, 'audio_codec': prepared['audio_codec'] if prepared else 'pcm16',
                  'audio_fallback_reason': prepared.get('audio_fallback_reason','') if prepared else 'No template; normalized PCM only',
                  'bundle_bytes': prepared['bundle']['bytes'] if prepared else 0, 'deployed': False, 'output_directory': str(destination),
                  'preview': str(destination/'media/preview.wav'), 'pipeline_commit': '098897736e089107704ec1633daff8922087fcc8'}
        if prepared:
            report['level_id'] = prepared['level_id']
        with zipfile.ZipFile(result/'prepared-song.zip', 'x', zipfile.ZIP_DEFLATED) as z:
            for folder in ('bundle', 'media') if prepared else ('normalized', 'media'):
                for file in sorted((result/folder).rglob('*')):
                    if file.is_file():
                        check(); z.write(file, str(file.relative_to(result)))
            z.writestr('preparation-report.json', json.dumps(report, indent=2))
        report['cache_files'] = {str(p.relative_to(result)):digest(p) for p in sorted(result.rglob('*')) if p.is_file()}
        (result/'report.json').write_text(json.dumps(report, indent=2))
        check()
        if digest(archive) != identity or (template and digest(template) != template_hash):
            raise ValueError('Song or template changed during preparation; try again')
        result.rename(destination)
    return json.dumps(report)
