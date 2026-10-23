/* Board contract: private rail list, ordered enable, and failure unwinding. */
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#define ENOMEM 12
#define GFP_KERNEL 0
#define MSM_DSI_VER_MAJOR_V2 2
#define MSM_DSI_V2_VER_MINOR_8064 0
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
struct device { int unused; };
struct platform_device { struct device dev; };
struct regulator { int id; };
struct regulator_bulk_data { const char *supply; unsigned init_load_uA; struct regulator *consumer; };
struct msm_dsi_config { const struct regulator_bulk_data *regulator_data; int num_regulators; int unrelated; };
struct msm_dsi_cfg_handler { unsigned major, minor; const struct msm_dsi_config *cfg; };
struct msm_dsi_host { struct platform_device *pdev; const struct msm_dsi_cfg_handler *cfg_hnd; struct regulator_bulk_data *supplies; };
static bool is_yuga = true;
static int calls[16], count, failed;
static bool of_machine_is_compatible(const char *name) { return is_yuga && !strcmp(name, "sony,xperia-yuga"); }
static void *devm_kmemdup(struct device *dev, const void *src, unsigned size, int flag) { void *p; (void)dev; (void)flag; p = malloc(size); if (p) memcpy(p, src, size); return p; }
static int regulator_enable(struct regulator *reg) { calls[count++] = reg->id; return failed == reg->id ? -5 : 0; }
static int regulator_disable(struct regulator *reg) { calls[count++] = -reg->id; return 0; }
static void usleep_range(int low, int high) { calls[count++] = low == 25000 && high == 26000 ? 25 : -100; }
static int regulator_bulk_enable(int n, struct regulator_bulk_data *s) { (void)n; (void)s; calls[count++] = 77; return 0; }
#include "../yuga-dsi-power.h"

static bool sequence(const int *expected, int n)
{
	return count == n && !memcmp(calls, expected, n * sizeof(int));
}

int main(void)
{
	struct msm_dsi_config original = { .num_regulators = 3, .unrelated = 99 };
	struct msm_dsi_cfg_handler handler = { .major = 2, .minor = 0, .cfg = &original };
	struct platform_device pdev = { 0 };
	struct regulator rails[] = { { 1 }, { 2 } };
	struct regulator_bulk_data supplies[] = { { .consumer = &rails[0] }, { .consumer = &rails[1] } };
	struct msm_dsi_host host = { .pdev = &pdev, .cfg_hnd = &handler, .supplies = supplies };
	const int good[] = { 1, 25, 2 }, second_failure[] = { 1, 25, 2, -1 }, first_failure[] = { 1 }, bulk[] = { 77 };
	if (yuga_dsi_configure(&host)) return 1;
	if (host.cfg_hnd == &handler || host.cfg_hnd->cfg == &original) return 2;
	if (host.cfg_hnd->cfg->num_regulators != 2 || original.num_regulators != 3 || host.cfg_hnd->cfg->unrelated != 99) return 3;
	if (strcmp(host.cfg_hnd->cfg->regulator_data[0].supply, "vddio") || strcmp(host.cfg_hnd->cfg->regulator_data[1].supply, "vdda")) return 4;
	if (yuga_dsi_regulators_enable(&host) || !sequence(good, 3)) return 5;
	count = 0; failed = 2;
	if (yuga_dsi_regulators_enable(&host) != -5 || !sequence(second_failure, 4)) return 6;
	count = 0; failed = 1;
	if (yuga_dsi_regulators_enable(&host) != -5 || !sequence(first_failure, 1)) return 7;
	free((void *)host.cfg_hnd->cfg); free((void *)host.cfg_hnd);
	is_yuga = false; count = 0; host.cfg_hnd = &handler;
	if (yuga_dsi_configure(&host) || host.cfg_hnd != &handler) return 8;
	if (yuga_dsi_regulators_enable(&host) || !sequence(bulk, 1)) return 9;
	return 0;
}
