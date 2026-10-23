import configparser
import importlib.util
import pathlib
import tempfile
import unittest

BASE = pathlib.Path(__file__).resolve().parents[1]


class NetworkProbe(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location('network_probe', BASE/'configure-network-probe.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def root(self, path):
        (path/'usr/lib').mkdir(parents=True)
        (path/'usr/lib/os-release').write_text('ID=ubuntu\nVERSION_ID="26.10"\n')
        return path

    def test_target_and_network_configuration_keep_usb_unmanaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.root(pathlib.Path(tmp)/'root')
            self.load().configure(root)
            nm = configparser.ConfigParser()
            nm.read(root/'etc/NetworkManager/conf.d/90-yuga-probe.conf')
            self.assertEqual(nm['keyfile']['unmanaged-devices'], 'interface-name:usb0')
            unit = configparser.ConfigParser()
            unit.read(root/'etc/systemd/system/yuga-probe.target.d/20-network.conf')
            self.assertIn('NetworkManager.service', unit['Unit']['Wants'].split())
            ssh = (root/'etc/ssh/sshd_config.d/10-yuga-probe.conf').read_text()
            self.assertIn('ListenAddress 0.0.0.0\n', ssh)
            self.assertIn('PasswordAuthentication no\n', ssh)
            self.assertIn('AuthenticationMethods publickey\n', ssh)
            self.assertFalse(list(root.rglob('*.nmconnection')))
            self.assertFalse(list(root.rglob('ssh_host_*')))

    def test_rejects_wrong_distribution_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.root(pathlib.Path(tmp)/'root')
            (root/'usr/lib/os-release').write_text('ID=ubuntu\nVERSION_ID="20.04"\n')
            with self.assertRaises(ValueError):
                self.load().configure(root)
            self.assertFalse((root/'etc').exists())

    def test_rejects_duplicate_distribution_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.root(pathlib.Path(tmp)/'root')
            with (root/'usr/lib/os-release').open('a') as output:
                output.write('ID=debian\n')
            with self.assertRaises(ValueError):
                self.load().configure(root)
            self.assertFalse((root/'etc').exists())

    def test_symlink_escape_rejected_before_any_configuration_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.root(pathlib.Path(tmp)/'root')
            outside = pathlib.Path(tmp)/'outside'
            outside.mkdir()
            (root/'etc').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.load().configure(root)
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
