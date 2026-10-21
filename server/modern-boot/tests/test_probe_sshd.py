import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1]/'validate-probe-sshd.py'
GOOD = '''Port 22
ListenAddress 172.16.42.1:22
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
'''


class ProbeSshd(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'Probe SSH validator not implemented')
        spec = importlib.util.spec_from_file_location('probe_sshd', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_actual_openssh105_canonical_case_accepted(self):
        self.module.validate(GOOD)

    def test_older_lowercase_fields_accepted(self):
        self.module.validate(GOOD.lower())

    def test_password_authentication_refused(self):
        with self.assertRaisesRegex(ValueError, 'passwordauthentication'):
            self.module.validate(GOOD.replace('PasswordAuthentication no', 'PasswordAuthentication yes'))

    def test_non_usb_listener_refused(self):
        with self.assertRaisesRegex(ValueError, 'listenaddress'):
            self.module.validate(GOOD.replace('172.16.42.1:22', '0.0.0.0:22'))

    def test_ambiguous_duplicate_field_refused(self):
        with self.assertRaisesRegex(ValueError, 'port'):
            self.module.validate(GOOD+'port 2222\n')


if __name__ == '__main__':
    unittest.main()
