import hashlib
import importlib.util
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import unittest

spec=importlib.util.spec_from_file_location('sender',Path(__file__).with_name('send-ut-image.py'))
sender=importlib.util.module_from_spec(spec); spec.loader.exec_module(sender)

class SenderTests(unittest.TestCase):
    def test_tcp_stream_to_real_receiver(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); dest=root/'dest'; dest.mkdir()
            data=bytes(range(256))*4097+b'tail'
            image=root/'source.img'; image.write_bytes(data)
            digest=hashlib.sha256(data).hexdigest()
            listener=socket.socket(); listener.bind(('127.0.0.1',0)); listener.listen(1)
            errors=[]
            def server():
                try:
                    with listener.accept()[0] as connection:
                        process=subprocess.Popen(['sh',str(Path(__file__).with_name('receive-ut-image.sh')),str(dest),'rootfs.img',str(len(data)),digest],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        ready=process.stdout.readline()
                        for byte in ready: connection.sendall(bytes([byte]))
                        while True:
                            block=connection.recv(521)
                            if not block: break
                            process.stdin.write(block)
                        process.stdin.close(); process.stdin=None
                        output,error=process.communicate(timeout=30)
                        if process.returncode: raise RuntimeError(error)
                        for byte in output: connection.sendall(bytes([byte]))
                except Exception as error: errors.append(error)
                finally: listener.close()
            thread=threading.Thread(target=server); thread.start()
            result=sender.send_image(image,'127.0.0.1',listener.getsockname()[1],'rootfs.img',digest,timeout=30)
            thread.join(30)
            self.assertFalse(thread.is_alive()); self.assertEqual(errors,[])
            self.assertEqual(result,'COMMITTED'); self.assertEqual((dest/'rootfs.img').read_bytes(),data)

    def test_wrong_identity_is_rejected_before_payload(self):
        with tempfile.TemporaryDirectory() as d:
            image=Path(d)/'source.img'; image.write_bytes(b'abc')
            listener=socket.socket(); listener.bind(('127.0.0.1',0)); listener.listen(1)
            received=[]
            def server():
                with listener.accept()[0] as connection:
                    connection.sendall(b'READY system.img 3 '+b'0'*64+b'\n')
                    received.append(connection.recv(100))
                listener.close()
            port=listener.getsockname()[1]
            thread=threading.Thread(target=server); thread.start()
            with self.assertRaises(ValueError): sender.send_image(image,'127.0.0.1',port,'rootfs.img',hashlib.sha256(b'abc').hexdigest(),timeout=5)
            thread.join(10); self.assertEqual(received,[b''])

    def test_local_hash_mismatch_prevents_connect(self):
        with tempfile.TemporaryDirectory() as d:
            image=Path(d)/'source.img'; image.write_bytes(b'abc')
            with self.assertRaises(ValueError): sender.send_image(image,'127.0.0.1',1,'rootfs.img','0'*64,timeout=1)

    def test_final_receipt_and_idempotence(self):
        for mode in ('wrong_commit', 'missing_commit', 'already_committed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d:
                image=Path(d)/'source.img'; image.write_bytes(b'abc')
                digest=hashlib.sha256(b'abc').hexdigest()
                identity=f'rootfs.img 3 {digest}\n'.encode()
                listener=socket.socket(); listener.bind(('127.0.0.1',0)); listener.listen(1)
                port=listener.getsockname()[1]; received=[]
                def server():
                    with listener.accept()[0] as connection:
                        connection.settimeout(5)
                        connection.sendall((b'ALREADY_COMMITTED ' if mode=='already_committed' else b'READY ')+identity)
                        payload=b''
                        while block:=connection.recv(100): payload+=block
                        received.append(payload)
                        if mode=='wrong_commit': connection.sendall(b'COMMITTED system.img 3 '+digest.encode()+b'\n')
                    listener.close()
                thread=threading.Thread(target=server); thread.start()
                if mode=='already_committed':
                    self.assertEqual(sender.send_image(image,'127.0.0.1',port,'rootfs.img',digest,timeout=5),'ALREADY_COMMITTED')
                else:
                    with self.assertRaises(ValueError): sender.send_image(image,'127.0.0.1',port,'rootfs.img',digest,timeout=5)
                thread.join(10); self.assertFalse(thread.is_alive())
                self.assertEqual(received,[b'' if mode=='already_committed' else b'abc'])

if __name__=='__main__': unittest.main()
