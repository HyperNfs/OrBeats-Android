"""Runs inside console_library_probe's socket-forbidden FakeFTP scope."""
import library_manager as manager
import release_updates as updates
import extras_manager as extras


def remove(snapshot, song=old_song):
    return json.loads(android.remove('192.168.1.2',2121,song['id'],root/'recovery',snapshot['library_sha256'],snapshot['plugin_sha256']))

# A removal must retain every other descriptor and its exact files.
other={**old_song,'id':'bsd_additive_'+'f'*24};two=copy.deepcopy(files)
two[BASE+'/library.bin']=library.encode([old_song,other]);two.update(zip(library.paths(other),(retained[p] for p in library.paths(old_song))))
reset(two);result=remove(status())
assert library.decode(FakeFTP.files[BASE+'/library.bin'])==[other]
assert all(FakeFTP.files[p]==two[p] for p in library.paths(other))
# Removal publishes exclusion BEFORE exact owned file cleanup, retaining the last template.
reset(files);snapshot=status();result=remove(snapshot)
assert result['ok'] and library.decode(FakeFTP.files[BASE+'/library.bin'])==[]
assert FakeFTP.files[BASE+'/template.bundle']==retained[library.paths(old_song)[0]]
assert all(p not in FakeFTP.files for p in library.paths(old_song))
assert all(FakeFTP.files[p]==b for p,b in historical.items())
publish=next(i for i,o in enumerate(FakeFTP.ops) if o[0]=='RENAME' and o[2]==BASE+'/library.bin')
assert all(i>publish for i,o in enumerate(FakeFTP.ops) if o[0]=='DELE' and o[1] in library.paths(old_song))
reset(files);snapshot=status();FakeFTP.files[BASE+'/library.bin']=library.encode([])
refused(lambda:remove(snapshot),'changed');assert not FakeFTP.ops
reset(files);snapshot=status();FakeFTP.dirs.add(BASE+'/.install-lock')
refused(lambda:remove(snapshot),'transaction');assert not FakeFTP.ops
reset(files);snapshot=status();FakeFTP.running=True
refused(lambda:remove(snapshot),'close');assert not FakeFTP.ops
reset(files);snapshot=status();FakeFTP.fail='publish'
refused(lambda:remove(snapshot),'simulated');assert FakeFTP.files[BASE+'/library.bin']==files[BASE+'/library.bin']
assert all(FakeFTP.files[p]==b for p,b in retained.items())
reset(files);snapshot=status();FakeFTP.fail='cleanup-song';result=remove(snapshot)
assert result['cleanup_pending'] and library.decode(FakeFTP.files[BASE+'/library.bin'])==[]
print('PASS: APK upstream confirmed removal, index-first/exact paths, last-template retention, stale snapshot/lock/game refusals, rollback and committed-cleanup reporting',flush=True)

# Actual official artifacts are private developer fixtures, never APK assets.
fixture=os.environ.get('ORBEATS_PLUGIN_PROBE_RELEASE')
if not fixture:raise AssertionError('Set private verified official plugin release fixture')
proof=json.loads(Path(fixture).read_text());manifest,prefix=proof['manifest'],proof['prefix']
blobs={row['asset']:(Path(proof['root'])/row['asset']).read_bytes() for row in manifest['plugins'].values()}
for row in manifest['plugins'].values():
    assert len(blobs[row['asset']])==row['bytes'] and hashlib.sha256(blobs[row['asset']]).hexdigest()==row['sha256']
original_release,original_read=updates.release,updates.read
updates.release=lambda:(copy.deepcopy(manifest),prefix)
def read(url,limit):
    assert url.startswith(prefix)
    blob=blobs[url[len(prefix):]];assert len(blob)<=limit;return blob
updates.read=read
try:
    canonical=manager.elf_from_fself(blobs['orbeats.prx'])
    base=copy.deepcopy(files);base['/data/GoldHEN/plugins/orbeats.prx']=canonical
    compatible_cap={**cap,'active_elf_sha256':hashlib.sha256(canonical).hexdigest()}
    base[BASE+'/companion-protocol.json']=json.dumps(compatible_cap).encode()
    ini=b'; unrelated settings\r\n[CUSA99999]\r\n/data/GoldHEN/plugins/other.prx\r\n[CUSA12878]\r\n/data/GoldHEN/plugins/orbeats.prx=false\r\n'
    base['/data/GoldHEN/plugins.ini']=ini
    for kind in ('main','extras'):
        reset(base)
        result=json.loads(android.install_plugin('192.168.1.2',2121,kind,root/'recovery'))
        assert result['ok'] and FakeFTP.files[BASE+'/library.bin']==base[BASE+'/library.bin']
        assert FakeFTP.files['/data/GoldHEN/AFR/CUSA12878/features.json']==base['/data/GoldHEN/AFR/CUSA12878/features.json']
        assert all(FakeFTP.files[p]==b for p,b in retained.items())
        assert b'[CUSA99999]\r\n/data/GoldHEN/plugins/other.prx\r\n' in FakeFTP.files['/data/GoldHEN/plugins.ini']
        target='/data/GoldHEN/plugins/'+('orbeats.prx' if kind=='main' else 'orbeats_extras.prx')
        installed=FakeFTP.files[target]
        assert (installed if installed.startswith(b'\x7fELF') else manager.elf_from_fself(installed))==manager.elf_from_fself(blobs[target.rsplit('/',1)[1]])
        if kind=='main':
            assert b'orbeats.prx=false' not in FakeFTP.files['/data/GoldHEN/plugins.ini']
            last=next(i for i,o in enumerate(FakeFTP.ops) if o[0]=='RENAME' and o[2]==BASE+'/companion-protocol.json')
            assert all(i<=last for i,o in enumerate(FakeFTP.ops) if o[0]=='RENAME')
        else:
            assert extras.registration(FakeFTP.files['/data/GoldHEN/plugins.ini'])=='enabled'
            assert FakeFTP.files[BASE+'/companion-protocol.json']==base[BASE+'/companion-protocol.json']
        reset(base);FakeFTP.fail='publish-ini'
        refused(lambda:android.install_plugin('192.168.1.2',2121,kind,root/'recovery'),'simulated')
        assert all(FakeFTP.files[p]==b for p,b in base.items())
    reset({});result=json.loads(android.install_plugin('192.168.1.2',2121,'main',root/'recovery'))
    assert result['ok'] and library.decode(FakeFTP.files[BASE+'/library.bin'])==[]
    reset(base);FakeFTP.dirs.add(BASE+'/.install-lock')
    refused(lambda:android.install_plugin('192.168.1.2',2121,'main',root/'recovery'),'transaction');assert not FakeFTP.ops
    reset(base);FakeFTP.files['/data/GoldHEN/plugins/orbeats.prx']=b'unknown plugin'
    refused(lambda:android.install_plugin('192.168.1.2',2121,'main',root/'recovery'),'Unrecognized');assert not FakeFTP.ops
    reset(base);FakeFTP.files['/data/GoldHEN/plugins/orbeats.prx']=canonical.replace(b'v0.8079',b'v0.9999')
    refused(lambda:android.install_plugin('192.168.1.2',2121,'main',root/'recovery'),'newer');assert not FakeFTP.ops
    reset(base);del FakeFTP.files[BASE+'/library.bin']
    refused(lambda:android.install_plugin('192.168.1.2',2121,'main',root/'recovery'),'Missing library');assert not FakeFTP.ops
    reset(base);FakeFTP.running=True
    refused(lambda:android.install_plugin('192.168.1.2',2121,'extras',root/'recovery'),'close');assert not FakeFTP.ops
    reset(base);updates.read=lambda *a:b'corrupt artifact'
    refused(lambda:android.install_plugin('192.168.1.2',2121,'main',root/'recovery'),'integrity');assert not FakeFTP.ops
    print('PASS: APK official main/Extras artifacts with simulated FTP, INI enable/preservation, existing-library/features retention, fresh empty setup, capability-last, rollback and integrity/unknown-plugin/lock refusals',flush=True)
finally:
    updates.release,updates.read=original_release,original_read
