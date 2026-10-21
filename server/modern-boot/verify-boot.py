#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys

path = pathlib.Path(__file__).with_name('pack-boot.py')
spec = importlib.util.spec_from_file_location('bootpack', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    module.verify_image(pathlib.Path(sys.argv[1]).read_bytes(), json.loads(pathlib.Path(sys.argv[2]).read_text()))
except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
    print('Boot validation failed:', error, file=sys.stderr)
    sys.exit(1)
print('Yuga diagnostic boot structure, component hashes and boot ID verified')
