// SPDX-License-Identifier: GPL-2.0-only
/* Sharp LS050T3SX01 / Renesas R63311, Sony Xperia Z (Yuga).
 * Command data and timing from Sony Mobile's GPLv2 2012-2013
 * mipi_dsi_panel_r63311_sharp_ls050t3sx01.c and fusion3 display board code.
 */
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/module.h>
#include <linux/of.h>
#include <drm/drm_connector.h>
#include <drm/drm_modes.h>
#include <drm/drm_mipi_dsi.h>
#include <drm/drm_panel.h>

struct yuga_panel {
	struct drm_panel panel;
	struct mipi_dsi_device *dsi;
	struct gpio_desc *reset;
	struct gpio_desc *dcdc;
};

static struct yuga_panel *to_yuga(struct drm_panel *panel)
{
	return container_of(panel, struct yuga_panel, panel);
}

static void yuga_power_off(struct yuga_panel *ctx)
{
	gpiod_set_value_cansleep(ctx->reset, 1);
	usleep_range(11000, 12000);
	gpiod_set_value_cansleep(ctx->dcdc, 0);
	usleep_range(25000, 26000);
}

static int yuga_prepare(struct drm_panel *panel)
{
	struct yuga_panel *ctx = to_yuga(panel);
	struct mipi_dsi_multi_context dsi_ctx = { .dsi = ctx->dsi };

	ctx->dsi->mode_flags |= MIPI_DSI_MODE_LPM;
	/* Host has already sequenced L29 then L2. Reset GPIO is active low. */
	gpiod_set_value_cansleep(ctx->dcdc, 1);
	gpiod_set_value_cansleep(ctx->reset, 1);
	usleep_range(25000, 26000);
	gpiod_set_value_cansleep(ctx->reset, 0);
	usleep_range(11000, 12000);
	mipi_dsi_dcs_exit_sleep_mode_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 150);
	if (dsi_ctx.accum_err)
		yuga_power_off(ctx);
	dev_info(panel->dev, "Yuga panel prepare: %d\n", dsi_ctx.accum_err);
	return dsi_ctx.accum_err;
}

static int yuga_enable(struct drm_panel *panel)
{
	struct yuga_panel *ctx = to_yuga(panel);
	struct mipi_dsi_multi_context dsi_ctx = { .dsi = ctx->dsi };

	/* Sony dlogo panel requires video data before DISPLAY_ON. */
	/* panel_display_on() in the working Sony driver selects HS TX mode. */
	ctx->dsi->mode_flags &= ~MIPI_DSI_MODE_LPM;
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xb0, 0x04);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x00);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
		0x0f, 0x13, 0x17, 0x1d, 0x28, 0x3c, 0x2a, 0x42, 0x4f, 0x5d, 0x6c, 0x75,
		0x0f, 0x14, 0x18, 0x1e, 0x2a, 0x3e, 0x2d, 0x46, 0x54, 0x62, 0x70, 0x78);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc8,
		0x20, 0x23, 0x26, 0x2b, 0x32, 0x43, 0x2d, 0x42, 0x4f, 0x5d, 0x6c, 0x75,
		0x22, 0x25, 0x28, 0x2d, 0x34, 0x46, 0x30, 0x46, 0x54, 0x62, 0x70, 0x78);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc9,
		0x1a, 0x22, 0x27, 0x2d, 0x36, 0x45, 0x2e, 0x43, 0x52, 0x62, 0x6f, 0x75,
		0x1b, 0x23, 0x28, 0x2f, 0x38, 0x48, 0x32, 0x47, 0x57, 0x66, 0x73, 0x78);
	mipi_dsi_dcs_set_display_on_multi(&dsi_ctx);
	dev_info(panel->dev, "Yuga panel display on: %d\n", dsi_ctx.accum_err);
	return dsi_ctx.accum_err;
}

static int yuga_disable(struct drm_panel *panel)
{
	struct yuga_panel *ctx = to_yuga(panel);
	struct mipi_dsi_multi_context dsi_ctx = { .dsi = ctx->dsi };

	mipi_dsi_dcs_set_display_off_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 20);
	mipi_dsi_dcs_enter_sleep_mode_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 100);
	return dsi_ctx.accum_err;
}

static int yuga_unprepare(struct drm_panel *panel)
{
	yuga_power_off(to_yuga(panel));
	return 0;
}

static const struct drm_display_mode yuga_mode = {
	/* 898 MHz measured PLL / 2 / 3; match the 100 kHz RCG tolerance. */
	.clock = 149667,
	.hdisplay = 1080, .hsync_start = 1214, .hsync_end = 1230, .htotal = 1294,
	.vdisplay = 1920, .vsync_start = 1924, .vsync_end = 1926, .vtotal = 1930,
	.width_mm = 62, .height_mm = 110,
	.type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED,
};

static int yuga_get_modes(struct drm_panel *panel, struct drm_connector *connector)
{
	struct drm_display_mode *mode = drm_mode_duplicate(connector->dev, &yuga_mode);

	if (!mode)
		return -ENOMEM;
	drm_mode_set_name(mode);
	drm_mode_probed_add(connector, mode);
	connector->display_info.width_mm = 62;
	connector->display_info.height_mm = 110;
	return 1;
}

static const struct drm_panel_funcs yuga_funcs = {
	.prepare = yuga_prepare, .enable = yuga_enable,
	.disable = yuga_disable, .unprepare = yuga_unprepare,
	.get_modes = yuga_get_modes,
};

static int yuga_probe(struct mipi_dsi_device *dsi)
{
	struct yuga_panel *ctx;
	int ret;

	ctx = devm_drm_panel_alloc(&dsi->dev, struct yuga_panel, panel,
				   &yuga_funcs, DRM_MODE_CONNECTOR_DSI);
	if (IS_ERR(ctx))
		return PTR_ERR(ctx);
	ctx->dsi = dsi;
	ctx->reset = devm_gpiod_get(&dsi->dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(ctx->reset))
		return dev_err_probe(&dsi->dev, PTR_ERR(ctx->reset), "reset GPIO\n");
	ctx->dcdc = devm_gpiod_get(&dsi->dev, "dcdc-en", GPIOD_OUT_LOW);
	if (IS_ERR(ctx->dcdc))
		return dev_err_probe(&dsi->dev, PTR_ERR(ctx->dcdc), "DCDC GPIO\n");
	/* DSI host rails and clocks must be ready before prepare sends commands. */
	ctx->panel.prepare_prev_first = true;
	ret = drm_panel_of_backlight(&ctx->panel);
	if (ret)
		return ret;
	dsi->lanes = 4;
	dsi->format = MIPI_DSI_FMT_RGB888;
	dsi->mode_flags = MIPI_DSI_MODE_VIDEO | MIPI_DSI_MODE_VIDEO_HSE | MIPI_DSI_MODE_LPM;
	mipi_dsi_set_drvdata(dsi, ctx);
	drm_panel_add(&ctx->panel);
	ret = mipi_dsi_attach(dsi);
	if (ret)
		drm_panel_remove(&ctx->panel);
	return ret;
}

static void yuga_remove(struct mipi_dsi_device *dsi)
{
	struct yuga_panel *ctx = mipi_dsi_get_drvdata(dsi);

	mipi_dsi_detach(dsi);
	drm_panel_remove(&ctx->panel);
}

static const struct of_device_id yuga_matches[] = {
	{ .compatible = "sharp,ls050t3sx01" }, { }
};
MODULE_DEVICE_TABLE(of, yuga_matches);
static struct mipi_dsi_driver yuga_driver = {
	.probe = yuga_probe, .remove = yuga_remove,
	.driver = { .name = "panel-sharp-ls050t3sx01", .of_match_table = yuga_matches },
};
module_mipi_dsi_driver(yuga_driver);
MODULE_DESCRIPTION("Sony Yuga Sharp LS050T3SX01 R63311 panel");
MODULE_LICENSE("GPL");
