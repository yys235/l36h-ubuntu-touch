/* Fixed-purpose RAM-resident reboot helper for the yuga diagnostic shell. */
#include <linux/reboot.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    (void)argv;
    if (argc != 1) {
        fputs("usage: reboot-bootloader (no arguments)\n", stderr);
        return 2;
    }
    sync();
    if (syscall(SYS_reboot, (unsigned int)LINUX_REBOOT_MAGIC1,
                (unsigned int)LINUX_REBOOT_MAGIC2,
                (unsigned int)LINUX_REBOOT_CMD_RESTART2, "bootloader") < 0) {
        perror("reboot bootloader");
        return 1;
    }
    return 0;
}
