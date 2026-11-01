"""Android bridge to the pinned OrBeats installer, not a new library protocol.

Song install/removal and official plugin deployment require explicit confirmation.
No automatic recovery, legacy song migration, batch writes or game launch.
"""
from contextlib import contextmanager
import hashlib
import ipaddress
import json
from pathlib import Path
import tempfile
import time
from ftplib import FTP, error_perm
from types import SimpleNamespace

import song_loader as loader


def address(host, port):
    ip = ipaddress.IPv4Address(host)
    if not any(ip in ipaddress.IPv4Network(net) for net in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
        raise ValueError('Use the PS4 private IPv4 address on your trusted LAN')
    if isinstance(port, bool) or not str(port).isdigit() or not 1 <= int(port) <= 65535:
        raise ValueError('Invalid FTP port')
    return str(ip), int(port)


class Session(FTP):
    """Bounded transfers; ignore thread cancellation only after a write starts.

    Once installation starts, finish/rollback rather than interrupt publication.
    Socket errors still fail closed; an interrupted process needs manual recovery.
    """
    def __init__(self):
        super().__init__()
        self.writing = False

    def guard(self):
        if not self.writing:
            loader.cancelled()

    def connect(self, host, port=2121, timeout=30, **kwargs):
        host, port = address(host, port)
        self.guard()
        return super().connect(host, port, timeout=30, **kwargs)

    def retrbinary(self, cmd, callback, blocksize=65536, rest=None):
        self.guard()
        deadline = time.monotonic()+120
        def collect(data):
            self.guard()
            if time.monotonic() > deadline:
                raise TimeoutError('FTP read exceeded two minutes; inspect before retrying')
            callback(data)
        return super().retrbinary(cmd, collect, blocksize, rest)

    def nlst(self, *args):
        self.guard()
        lines, size = [], 0
        deadline = time.monotonic()+120
        def collect(line):
            nonlocal size
            self.guard()
            size += len(line.encode('utf-8'))
            if len(lines) >= 4096 or size > 1048576:
                raise ValueError('FTP directory listing exceeds safety bounds')
            if time.monotonic() > deadline:
                raise TimeoutError('FTP directory listing exceeded two minutes')
            lines.append(line)
        self.retrlines('NLST'+''.join(' '+arg for arg in args), collect)
        return lines

    def storbinary(self, cmd, file, blocksize=65536, callback=None, rest=None):
        self.guard(); self.writing = True
        deadline = time.monotonic()+120
        def sent(data):
            if time.monotonic() > deadline:
                raise TimeoutError('FTP upload exceeded two minutes; inspect before retrying')
            if callback: callback(data)
        return super().storbinary(cmd, file, blocksize, sent, rest)

    def mkd(self, path):
        self.guard(); self.writing = True
        return super().mkd(path)


def modules():
    pipeline = loader.pipeline()
    import additive_companion as core
    import additive_library as library
    return pipeline, core, library


def read_library(ftp, core, library):
    # Never fall back to compiled historical songs on an absent/denied manifest.
    raw = core.read(ftp, library.BASE+'/library.bin', library.MAX_BYTES+1, missing=True)
    if raw is None:
        raise ValueError('No OrBeats library index. Complete official OrBeats setup first; no files changed.')
    return library.decode(raw), raw


def inspect(ftp, core, library):
    core.closed(ftp)
    cap = json.loads(core.read(ftp, library.BASE+'/companion-protocol.json', 4096))
    if cap.get('schema') != 1 or cap.get('title') != 'CUSA12878':
        raise ValueError('A companion-capable OrBeats plugin for CUSA12878 is required')
    plugin = core.read(ftp, '/data/GoldHEN/plugins/orbeats.prx', 2000000)
    if hashlib.sha256(plugin).hexdigest() != cap.get('active_elf_sha256'):
        raise ValueError('Plugin/capability mismatch; use the official OrBeats setup to repair it')
    flags = json.loads(core.read(ftp, '/data/GoldHEN/AFR/CUSA12878/features.json', 65536))
    if flags.get('enable_plugin') is not True or flags.get('enable_additive_song_packs') is not True:
        raise ValueError('The existing OrBeats additive pack is not enabled')
    if any(flags.get(k) for k in ('enable_custom_song_replacements', 'enable_song_metadata_modification', 'enable_beatmap_mode_mapping', 'enable_song_previews')):
        raise ValueError('Legacy replacement features must remain OFF')
    count, fmt = cap.get('max_songs', 8), cap.get('library_format', 1)
    if type(count) is not int or not 1 <= count <= 64 or type(fmt) is not int or not 1 <= fmt <= 4:
        raise ValueError('Unsupported OrBeats library capability')
    songs, raw = read_library(ftp, core, library)
    if len(songs) > count:
        raise ValueError('Library exceeds the installed plugin capacity')
    # A preexisting writer lock is never removed by this application.
    names = [p.rstrip('/').rsplit('/', 1)[-1] for p in ftp.nlst(library.BASE)]
    if '.install-lock' in names:
        raise ValueError('OrBeats has an active/interrupted install lock; inspect it before retrying')
    # Historical .backup- snapshots are harmless with the valid main index above.
    if any(n.startswith(('library.bin.rollback-', 'library.bin.stage-')) for n in names):
        raise ValueError('OrBeats has retained transaction recovery files (.rollback/.stage); inspect before retrying')
    return cap, songs, raw


def status(host, port):
    host, port = address(host, port)
    _, core, library = modules()
    ftp = Session()
    try:
        ftp.connect(host, port); ftp.login('anonymous', '')
        cap, songs, raw = inspect(ftp, core, library)
        return json.dumps({'songs': [{'id':s['id'], 'title':s['title'], 'author':s['author'],
                'cover_bytes':s.get('cover',{}).get('bytes',0), 'cover_fnv':str(s.get('cover',{}).get('fnv',0))} for s in songs],
            'max_songs':cap.get('max_songs', 8), 'library_format':cap.get('library_format', 1),
            'plugin_sha256':cap['active_elf_sha256'], 'library_sha256':hashlib.sha256(raw).hexdigest(),
            'closed':True, 'read_only':True})
    finally:
        ftp.close()


def cover(host,port,song_id,expected_bytes,expected_fnv):
    host,port=address(host,port)
    _,core,library=modules()
    path=library.paths({'id':song_id})[1]
    expected_fnv=int(expected_fnv)
    if type(expected_bytes) is not int or not 1<=expected_bytes<=4*1024*1024 or not 0<=expected_fnv<2**64:
        raise ValueError('Invalid indexed cover bounds')
    ftp=Session()
    try:
        ftp.connect(host,port);ftp.login('anonymous','')
        data=core.read(ftp,path,expected_bytes+1)
        if len(data)!=expected_bytes or library.fnv(data)!=expected_fnv:raise ValueError('PS4 cover changed or checksum mismatch; refresh library')
        return data
    finally:ftp.close()


def install(host, port, archive, expected_hash, state_dir, work_dir, local_template='', expected_library='', expected_plugin='', quality='original'):
    if quality not in loader.AUDIO_QUALITIES:raise ValueError('Unknown audio quality')
    host, port = address(host, port)
    if not expected_library or not expected_plugin:
        raise ValueError('Read and confirm the console library before installation')
    pipeline, core, library = modules()
    importer, v4, bundle, media = pipeline
    import console_transaction
    import score_source
    # Persistent app-private recovery, NEVER an evictable cache/extracted package.
    state_dir, work_dir = Path(state_dir), Path(work_dir)
    state_dir.mkdir(parents=True, exist_ok=True); work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='install-', dir=work_dir) as folder:
        source, _ = loader.verified_source(archive, expected_hash, Path(folder)/'source', loader.cancelled)
        ftp = Session()
        try:
            ftp.connect(host, port); ftp.login('anonymous', '')
            cap, songs, raw = inspect(ftp, core, library)
            if hashlib.sha256(raw).hexdigest() != expected_library or cap['active_elf_sha256'] != expected_plugin:
                raise ValueError('Console library/plugin changed since confirmation; refresh and confirm again')
        finally:
            ftp.close()
        # The upstream installer reconnects and guards every write. Retain the
        # confirmed snapshot across this gap; never silently append to new bytes.
        def confirmed_library(remote):
            entries, content = read_library(remote, core, library)
            if content != raw:
                raise ValueError('Console library changed before installation; refresh and confirm again')
            current = json.loads(core.read(remote, library.BASE+'/companion-protocol.json', 4096))
            if current != cap:
                raise ValueError('Console capability changed before installation')
            return entries, content
        audio_report={}
        def compressed_prepare(normalized, template, output, original_audio=None):
            loader.validate_template(template, lambda: None)
            original_audio=loader.quality_audio(normalized,original_audio,quality,adapter,bundle)
            manifest=bundle.prepare(normalized, template, output, original_audio=original_audio)
            audio_report.update(audio_quality=quality,audio_codec=manifest['audio_codec'],bundle_bytes=manifest['bundle']['bytes'],
                audio_fallback_reason=manifest.get('audio_fallback_reason',''))
            return manifest
        adapter = loader.audio_adapter(lambda: None)
        prepare_api = SimpleNamespace(**vars(bundle)); prepare_api.prepare = compressed_prepare
        # Upstream-created temporary folders can also use Android's cache alias.
        prepare_api.local_file = lambda root, name: bundle.local_file(Path(root).resolve(), name)
        helpers = {'import_v3_additive.py':importer, 'import_v4_additive.py':v4,
                   'prepare_additive_bundle.py':prepare_api, 'prepare_additive_media.py':media}
        before = (core.FTP, core.helper, core.load_library, console_transaction.LOCAL_BACKUPS,
                  score_source.original_hash, importer.subprocess, importer.v2.subprocess, media.subprocess)
        try:
            core.FTP = Session
            core.helper = lambda name: helpers[name]
            core.load_library = confirmed_library
            console_transaction.LOCAL_BACKUPS = state_dir/'transactions'
            # Use the verified ORIGINAL BeatSaver identity, even after V4 normalization.
            score_source.original_hash = lambda *args: expected_hash.lower()
            importer.subprocess = importer.v2.subprocess = media.subprocess = adapter
            result = core.install({'title':{'id':'CUSA12878'}, 'ps4':{'ip':host,'ftp_port':port},
                'additive_template':local_template}, song_dir=str(source), report_dir=state_dir/'reports')
            result.update(audio_report if not result.get('already_present') else {'audio_codec':'unchanged'})
            result['recovery_directory'] = str(state_dir)
            return json.dumps(result)
        finally:
            (core.FTP, core.helper, core.load_library, console_transaction.LOCAL_BACKUPS,
             score_source.original_hash, importer.subprocess, importer.v2.subprocess, media.subprocess) = before


def _names(ftp, folder):
    try:
        return [p.rstrip('/').rsplit('/', 1)[-1] for p in ftp.nlst(folder)]
    except error_perm as error:
        parent, name = folder.rsplit('/', 1)
        if not str(error).startswith('550') or not parent or name in _names(ftp, parent):
            raise
        return []


@contextmanager
def _management(host, port, state_dir, operation, expected_library='', expected_plugin='', release=None):
    host, port = address(host, port)
    _, core, codec = modules()
    import library_manager as manager
    import extras_manager as extras
    import release_updates as updates
    import console_transaction as transaction
    state = Path(state_dir).resolve(); state.mkdir(parents=True, exist_ok=True)
    original_connection, original_merge = manager.connection, manager.merge_ini
    before = (manager.FTP, manager.connection, manager.merge_ini, core.load_library, transaction.LOCAL_BACKUPS)

    def load(ftp):
        raw = core.read(ftp, codec.BASE+'/library.bin', codec.MAX_BYTES+1, missing=True)
        if operation == 'remove':
            if raw is None or hashlib.sha256(raw).hexdigest() != expected_library:
                raise ValueError('Library changed; refresh and confirm removal again')
        return (codec.decode(raw), raw) if raw is not None else ([], None)

    def merge(original):
        target = '/data/GoldHEN/plugins/orbeats.prx'
        if any(line.strip().startswith(target.encode()) for line in original.splitlines()):
            saved = extras.TARGET
            try:
                extras.TARGET = target
                original = extras.registration(original, True)
            finally:
                extras.TARGET = saved
        return original_merge(original)

    @contextmanager
    def connection(config, write=False):
        with original_connection(config, False) as ftp:
            core.closed(ftp)
            names = _names(ftp, codec.BASE)
            if '.install-lock' in names or any('.rollback-' in n or '.stage-' in n for n in names):
                raise ValueError('Active/interrupted OrBeats transaction; inspect recovery before management')
            if 'library.bin' not in names and any(n.startswith('library.bin.backup-') or n.endswith('.bundle') and n != 'template.bundle' for n in names):
                raise ValueError('Missing library with retained songs/backups; recover before management')
            if 'library.bin' in names:
                load(ftp)  # Validate even when only updating a plugin.
            if operation == 'remove':
                cap, _, raw = inspect(ftp, core, codec)
                if cap['active_elf_sha256'] != expected_plugin or hashlib.sha256(raw).hexdigest() != expected_library:
                    raise ValueError('Console changed; refresh and confirm removal again')
            else:
                path = '/data/GoldHEN/plugins/'+('orbeats.prx' if operation == 'main' else 'orbeats_extras.prx')
                # Never overwrite an unknown binary or downgrade a newer local build.
                if path.rsplit('/', 1)[-1] in _names(ftp, '/data/GoldHEN/plugins'):
                    current = core.read(ftp, path, 2000000)
                    version = manager.binary_version(current) if operation == 'main' else extras.version(current)
                    if version is None or updates.number(version) > updates.number(release['plugins'][operation]['version']):
                        raise ValueError('Unrecognized or newer installed plugin; refusing replacement')
                for folder in ('/data/GoldHEN', '/data/GoldHEN/plugins'):
                    if any(n.startswith(('plugins.ini.stage-', 'plugins.ini.rollback-', 'orbeats.prx.stage-', 'orbeats.prx.rollback-', 'orbeats_extras.prx.stage-', 'orbeats_extras.prx.rollback-')) for n in _names(ftp, folder)):
                        raise ValueError('Retained plugin transaction recovery; inspect before management')
            locked = False
            try:
                if write:
                    manager.acquire_install_lock(ftp); locked = True
                yield ftp
            finally:
                if locked:
                    try: ftp.rmd(codec.BASE+'/.install-lock')
                    except Exception: pass

    try:
        manager.FTP = Session
        manager.connection = connection
        manager.merge_ini = merge
        core.load_library = load
        transaction.LOCAL_BACKUPS = state/'transactions'
        yield {'title':{'id':'CUSA12878'}, 'ps4':{'ip':host,'ftp_port':port}}
    finally:
        manager.FTP, manager.connection, manager.merge_ini, core.load_library, transaction.LOCAL_BACKUPS = before


def remove(host, port, song_id, state_dir, expected_library, expected_plugin):
    if not expected_library or not expected_plugin:
        raise ValueError('Read and confirm the library before removal')
    with _management(host, port, state_dir, 'remove', expected_library, expected_plugin) as config:
        import library_manager as manager
        result = manager.remove(config, song_id)
        result['recovery_directory'] = str(Path(state_dir).resolve())
        return json.dumps(result)


def install_plugin(host, port, kind, state_dir):
    if kind not in ('main', 'extras'):
        raise ValueError('Unknown official plugin')
    modules()
    import release_updates as updates
    manifest, prefix = updates.release()
    original_release = updates.release
    try:
        updates.release = lambda: (manifest, prefix)
        with _management(host, port, state_dir, kind, release=manifest) as config:
            return json.dumps(updates.install(config, kind))
    finally:
        updates.release = original_release
