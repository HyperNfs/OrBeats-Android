#!/usr/bin/env python3
"""Host-only validation/cancellation tests; no network or Android imports."""
from pathlib import Path
import sys
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
import console_library as console

class Boundaries(unittest.TestCase):
    def test_missing_directory_is_not_permission_denied(self):
        missing=console.error_perm('550 unavailable')
        def listed(folder):
            if folder=='/data':return []
            raise missing
        self.assertEqual(console._names(SimpleNamespace(nlst=listed),'/data/additive'),[])
        def denied(folder):
            if folder=='/data':return ['/data/additive/']
            raise missing
        with self.assertRaises(console.error_perm):console._names(SimpleNamespace(nlst=denied),'/data/additive')
        def denied_login(folder):raise console.error_perm('530 denied')
        with self.assertRaises(console.error_perm):console._names(SimpleNamespace(nlst=denied_login),'/data/additive')
    def test_private_addresses(self):
        for host in ('10.0.0.1','172.16.0.1','172.31.255.254','192.168.1.2'):
            self.assertEqual(console.address(host,'2121'),(host,2121))
    def test_refused_addresses(self):
        for host in ('localhost','127.0.0.1','8.8.8.8','172.32.0.1','169.254.1.1','::1','192.168.1.2\nDELE /'):
            with self.assertRaises(ValueError):console.address(host,2121)
    def test_refused_ports(self):
        for port in (0,65536,True,'1\nDELE /','no'):
            with self.assertRaises(ValueError):console.address('192.168.1.2',port)
    def test_cancellation_before_write_only(self):
        session=console.Session()
        with patch.object(console.loader,'cancelled',side_effect=InterruptedError('Cancelled')):
            with self.assertRaises(InterruptedError):session.guard()
            session.writing=True
            session.guard()  # Finish/rollback a started transaction, do not abandon publication.
        session.close()
    def test_connect_uses_validated_ip_and_bounded_timeout(self):
        with patch.object(console.loader,'cancelled'),patch.object(console.FTP,'connect',return_value='220') as connect:
            self.assertEqual(console.Session().connect('192.168.1.2','2121',timeout=9999),'220')
            connect.assert_called_once_with('192.168.1.2',2121,timeout=30)
            with self.assertRaises(ValueError):console.Session().connect('8.8.8.8')
    def test_read_deadline_and_callback(self):
        def transfer(cmd,callback,*args):callback(b'payload');return '226'
        with patch.object(console.loader,'cancelled'),patch.object(console.FTP,'retrbinary',side_effect=transfer):
            session=console.Session();received=[]
            self.assertEqual(session.retrbinary('RETR fixed',received.append),'226')
            self.assertEqual(received,[b'payload'])
            with patch.object(console,'time',SimpleNamespace(monotonic=iter([0,121]).__next__)):
                with self.assertRaises(TimeoutError):session.retrbinary('RETR fixed',received.append)
    def test_directory_listing_bounds_and_deadline(self):
        def listing(cmd,callback):
            self.assertEqual(cmd,'NLST fixed')
            for line in content:callback(line)
        with patch.object(console.loader,'cancelled'),patch.object(console.FTP,'retrlines',side_effect=listing):
            session=console.Session();content=['one','two']
            self.assertEqual(session.nlst('fixed'),content)
            content=['x']*4097
            with self.assertRaises(ValueError):session.nlst('fixed')
            content=['x'*8192]*129
            with self.assertRaises(ValueError):session.nlst('fixed')
            content=['one']
            with patch.object(console,'time',SimpleNamespace(monotonic=iter([0,121]).__next__)):
                with self.assertRaises(TimeoutError):session.nlst('fixed')
    def test_upload_deadline_and_write_cancellation_boundary(self):
        def transfer(cmd,file,size,callback,rest):callback(file.read());return '226'
        with patch.object(console.loader,'cancelled') as cancel,patch.object(console.FTP,'storbinary',side_effect=transfer):
            session=console.Session();sent=[]
            self.assertEqual(session.storbinary('STOR fixed',io.BytesIO(b'payload'),callback=sent.append),'226')
            self.assertEqual(sent,[b'payload']);self.assertTrue(session.writing);cancel.assert_called_once()
            with patch.object(console,'time',SimpleNamespace(monotonic=iter([0,121]).__next__)):
                with self.assertRaises(TimeoutError):session.storbinary('STOR fixed',io.BytesIO(b'payload'))
    def test_writer_lock_attempt_disables_thread_cancellation(self):
        with patch.object(console.loader,'cancelled'),patch.object(console.FTP,'mkd',return_value='lock'):
            session=console.Session();self.assertEqual(session.mkd('lock'),'lock');self.assertTrue(session.writing)
    def test_confirmation_required_before_modules_or_network(self):
        with patch.object(console,'modules',side_effect=AssertionError('Should not import')):
            with self.assertRaisesRegex(ValueError,'confirm'):
                console.install('192.168.1.2',2121,'missing.zip','0'*40,'state','work')

if __name__=='__main__':unittest.main()
