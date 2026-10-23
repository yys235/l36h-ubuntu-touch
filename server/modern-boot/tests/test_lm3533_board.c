/* Register contract test for Sony's source-backed board settings. */
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#define ENOMEM 12
#define GFP_KERNEL 0
#define LM3533_BOOST_OVP_24V 1
#define LM3533_BOOST_FREQ_500KHZ 0
#define LM3533_REG_BOOST_PWM 0x2c
struct device { void *of_node; void *platform_data; };
struct lm3533_bl_platform_data { char *name; unsigned max_current; unsigned default_brightness; unsigned pwm; };
struct lm3533_platform_data { unsigned boost_ovp, boost_freq; struct lm3533_bl_platform_data *backlights; unsigned num_backlights; };
struct lm3533 { struct device *dev; };
static unsigned char regs[256];
static bool of_machine_is_compatible(const char *name) { return !strcmp(name, "sony,xperia-yuga"); }
static bool of_device_is_compatible(void *node, const char *name) { return node && !strcmp(name, "sony,yuga-lm3533"); }
static void *devm_kzalloc(struct device *dev, unsigned size, int flag) { (void)dev; (void)flag; return calloc(1, size); }
static int lm3533_update(struct lm3533 *chip, unsigned reg, unsigned val, unsigned mask) { (void)chip; regs[reg] = (regs[reg] & ~mask) | (val & mask); return 0; }
static int lm3533_set_hvled_config(struct lm3533 *chip, unsigned led, unsigned bank) { return lm3533_update(chip, 0x10, bank << (led - 1), 1 << (led - 1)); }
#include "../yuga-lm3533.h"

int main(void)
{
	struct device dev = { .of_node = (void *)1 };
	struct lm3533 chip = { .dev = &dev };
	struct lm3533_platform_data *data;
	/* Preserve other output routes; both HVLED anodes must use CPOUT. */
	regs[0x25] = 0xa0;
	regs[0x10] = 0xff;
	regs[0x1a] = 0xff;
	if (lm3533_yuga_platform_data(&dev) || lm3533_yuga_outputs(&chip)) return 1;
	data = dev.platform_data;
	if (regs[0x25] != 0xa3) return 2;
	if ((regs[0x10] & 3) || (regs[0x1a] & 3) != 2) return 3;
	if (!(regs[0x2c] & 8)) return 4;
	if (data->boost_ovp != 1 || data->boost_freq || data->num_backlights != 1) return 5;
	if (data->backlights->max_current != 20200 || data->backlights->pwm) return 6;
	free(data->backlights); free(data);
	return 0;
}
