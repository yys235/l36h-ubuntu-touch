"""Fix the packed two-byte header without changing dictionary format or ABI."""
from pathlib import Path
import sys

path = Path(sys.argv[1]) / 'src/storage/phrase_index.h'
old = 'return (*(guint32 *)(buf_begin + sizeof(guint8) + sizeof(guint8)));'
new = '''// The serialized header has two bytes before the frequency.
        // Copy into an aligned value: a guint32* cast can become an unaligned
        // VFP load on ARM, which Linux 3.4 cannot emulate.
        guint32 frequency;
        memcpy(&frequency, buf_begin + sizeof(guint8) + sizeof(guint8),
               sizeof(frequency));
        return frequency;'''
text = path.read_text()
assert text.count(old) == 1, 'unexpected source; do not patch'
path.write_text(text.replace(old, new))
