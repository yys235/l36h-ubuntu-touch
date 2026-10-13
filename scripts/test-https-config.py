import pathlib, subprocess, tempfile, unittest
script=pathlib.Path(__file__).with_name('render-https-config.py')
class HTTPSConfig(unittest.TestCase):
    def test_custom_ip_and_same_external_port(self):
        with tempfile.TemporaryDirectory() as d:
            out=pathlib.Path(d)/'generated'
            subprocess.run(['python3',str(script),'--host','192.168.1.50','--output',str(out)],check=True,capture_output=True)
            text=(out/'Caddyfile').read_text()
            self.assertIn('https://192.168.1.50:9119',text)
            self.assertIn('reverse_proxy 127.0.0.1:9120',text)
            self.assertIn('tls internal',text)
            self.assertNotIn('192.168.123.144',text)
    def test_invalid_host_and_port_collision_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for host, backend in [('bad\nconfig', '9120'),('192.168.1.50','9119')]:
                r=subprocess.run(['python3',str(script),'--host',host,'--backend-port',backend,'--output',str(pathlib.Path(d)/'out')],capture_output=True)
                self.assertNotEqual(r.returncode,0)
                self.assertFalse((pathlib.Path(d)/'out').exists())
if __name__=='__main__': unittest.main()
