import pathlib
import shlex
import subprocess
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1]/'build-systemd-probe.sh'


class ProbeBuild(unittest.TestCase):
    def test_package_inventory_has_real_tsv_separators(self):
        line = next(line for line in SCRIPT.read_text().splitlines() if 'chroot "$root" /usr/bin/dpkg-query' in line)
        arguments = shlex.split(line)
        format_arg = next(arg for arg in arguments if arg.startswith('-f='))
        result = subprocess.run(['dpkg-query', '-W', format_arg, 'dpkg'], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.count('\n'), 1)
        self.assertEqual(result.stdout.split('\t')[0], 'dpkg')
        self.assertEqual(len(result.stdout.strip().split('\t')), 3)


if __name__ == '__main__':
    unittest.main()
