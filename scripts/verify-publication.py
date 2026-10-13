"""Check SHA256SUMS with path containment and missing-file checks."""
import argparse, hashlib, pathlib
p = argparse.ArgumentParser()
p.add_argument('--root', type=pathlib.Path, required=True)
p.add_argument('--checksums', type=pathlib.Path, required=True)
a = p.parse_args()
root = a.root.resolve()
checked = 0
failures = []
for line in a.checksums.read_text(encoding='utf-8-sig').splitlines():
    digest, name = line.split('  ', 1)
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid SHA256 record')
    relative = pathlib.PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name:
        raise ValueError('Unsafe checksum path')
    path = root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root) or not path.is_file():
        failures.append(name + ': missing or unsafe')
        continue
    h = hashlib.sha256()
    with path.open('rb') as source:
        while chunk := source.read(1024 * 1024):
            h.update(chunk)
    if h.hexdigest() != digest:
        failures.append(name + ': checksum mismatch')
    else:
        checked += 1
for failure in failures:
    print(failure)
print(f'Checked {checked}; failures {len(failures)}')
raise SystemExit(1 if failures else 0)
