#!/usr/bin/env python3
"""Create an explicitly recorded DTB-only derivative of verified CI artifacts."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('adjust', HERE/'adjust-source.py')
adjust = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adjust)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    metadata = json.loads((args.input/'build-manifest.json').read_text())
    for name, item in metadata['files'].items():
        path = args.input/name
        if pathlib.PurePosixPath(name).name != name or path.is_symlink():
            raise ValueError('unsafe artifact name')
        data = path.read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('parent artifact hash/size mismatch: '+name)
    source = adjust.card_detect_pinconf((args.input/'yuga.dts').read_text())
    node = '/soc/pinctrl@800000/sdcc3-cd-pin-active-state'
    actual = subprocess.check_output(['fdtget', '-t', 's', str(args.input/'yuga.dtb'), node, 'function'], text=True).strip()
    if actual != 'gpio':
        raise ValueError('unexpected parent card-detect mux')
    args.output.mkdir(exist_ok=False)
    for name in metadata['files']:
        shutil.copyfile(args.input/name, args.output/name)
    subprocess.run(['fdtput', '-d', str(args.output/'yuga.dtb'), node, 'function'], check=True)
    properties = subprocess.check_output(['fdtget', '-p', str(args.output/'yuga.dtb'), node], text=True).splitlines()
    if 'function' in properties:
        raise ValueError('card-detect mux property not removed')
    (args.output/'yuga.dts').write_text(source)
    parent = metadata['files']['yuga.dtb']['sha256']
    for name in ('yuga.dtb', 'yuga.dts'):
        data = (args.output/name).read_bytes()
        metadata['files'][name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    metadata['dtb_derivation'] = {
        'parent_dtb_sha256': parent,
        'operation': 'remove function property from GPIO26 card-detect pinconf only',
        'tool': subprocess.check_output(['fdtput', '--version'], text=True).strip(),
        'kernel_and_modules': 'Unchanged verified CI artifacts; DTB is a local controlled derivative',
    }
    (args.output/'build-manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata['dtb_derivation']))


if __name__ == '__main__':
    main()
