"""Validate the reboot syscall contract without rebooting the build computer."""
from pathlib import Path
import subprocess
import tempfile

source = Path(__file__).with_name('reboot-bootloader.c')
with tempfile.TemporaryDirectory(prefix='ut-reboot-test-') as tmp:
    root = Path(tmp)
    fixture = root / 'fake-reboot.c'
    fixture.write_text(r'''
#include <assert.h>
#include <errno.h>
#include <linux/reboot.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
static int synced;
void fake_sync(void) { synced = 1; }
long fake_syscall(long number, ...) {
    va_list arguments;
    va_start(arguments, number);
    assert(synced && number == SYS_reboot);
    assert(va_arg(arguments, unsigned int) == LINUX_REBOOT_MAGIC1);
    assert(va_arg(arguments, unsigned int) == LINUX_REBOOT_MAGIC2);
    assert(va_arg(arguments, unsigned int) == LINUX_REBOOT_CMD_RESTART2);
    assert(strcmp(va_arg(arguments, const char *), "bootloader") == 0);
    va_end(arguments);
    puts("RESTART2_BOOTLOADER_VERIFIED");
    errno = EPERM;
    return -1;
}
''')
    executable = root / 'reboot-test'
    subprocess.run(['gcc', '-Wall', '-Wextra', '-Werror',
                    '-Dsync=fake_sync', '-Dsyscall=fake_syscall',
                    str(source), str(fixture), '-o', str(executable)], check=True)
    result = subprocess.run([str(executable)], capture_output=True, text=True)
    assert result.returncode == 1, result
    assert result.stdout.strip() == 'RESTART2_BOOTLOADER_VERIFIED', result
    assert 'Operation not permitted' in result.stderr, result
    for argument in ('recovery', 'system', 'bootloader', '--help'):
        result = subprocess.run([str(executable), argument], capture_output=True, text=True)
        assert result.returncode != 0, result
        assert not result.stdout, result  # The fake syscall was never reached.
    print('REBOOT_CONTRACT_TESTS_PASSED')
