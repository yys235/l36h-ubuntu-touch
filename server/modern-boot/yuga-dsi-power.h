/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after struct msm_dsi_host. Yuga has no APQ8064 avdd rail. */
static bool yuga_dsi_host(struct msm_dsi_host *host)
{
	return of_machine_is_compatible("sony,xperia-yuga") &&
		host->cfg_hnd->major == MSM_DSI_VER_MAJOR_V2 &&
		host->cfg_hnd->minor == MSM_DSI_V2_VER_MINOR_8064;
}

static int yuga_dsi_configure(struct msm_dsi_host *host)
{
	static const struct regulator_bulk_data supplies[] = {
		{ .supply = "vddio", .init_load_uA = 100000 }, /* L29 1.8 V */
		{ .supply = "vdda", .init_load_uA = 100000 }, /* L2 1.2 V */
	};
	struct device *dev = &host->pdev->dev;
	struct msm_dsi_cfg_handler *handler;
	struct msm_dsi_config *config;

	if (!yuga_dsi_host(host))
		return 0;
	config = devm_kmemdup(dev, host->cfg_hnd->cfg, sizeof(*config), GFP_KERNEL);
	handler = devm_kmemdup(dev, host->cfg_hnd, sizeof(*handler), GFP_KERNEL);
	if (!config || !handler)
		return -ENOMEM;
	config->regulator_data = supplies;
	config->num_regulators = ARRAY_SIZE(supplies);
	handler->cfg = config;
	host->cfg_hnd = handler;
	return 0;
}

static int yuga_dsi_regulators_enable(struct msm_dsi_host *host)
{
	int ret;

	if (!yuga_dsi_host(host))
		return regulator_bulk_enable(host->cfg_hnd->cfg->num_regulators,
					     host->supplies);
	/* Sony sequence: L29, 25 ms, L2, then panel DCDC and reset. */
	ret = regulator_enable(host->supplies[0].consumer);
	if (ret)
		return ret;
	usleep_range(25000, 26000);
	ret = regulator_enable(host->supplies[1].consumer);
	if (ret)
		regulator_disable(host->supplies[0].consumer);
	return ret;
}
