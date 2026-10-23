/* Exercise the actual panel callbacks against the Sony transfer contract. */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define MIPI_DSI_MODE_LPM 1
struct drm_panel { void *dev; };
struct mipi_dsi_device { unsigned mode_flags; };
struct mipi_dsi_multi_context { struct mipi_dsi_device *dsi; int accum_err; };
struct yuga_panel { struct mipi_dsi_device *dsi; void *reset, *dcdc; };
static struct mipi_dsi_device dsi;
static struct yuga_panel state = { .dsi = &dsi };
static unsigned commands[32], count;
static struct yuga_panel *to_yuga(struct drm_panel *panel) { (void)panel; return &state; }
static void gpiod_set_value_cansleep(void *gpio, int value) { (void)gpio; (void)value; }
static void usleep_range(int low, int high) { (void)low; (void)high; }
static void yuga_power_off(struct yuga_panel *ctx) { (void)ctx; }
static void mipi_dsi_msleep(struct mipi_dsi_multi_context *ctx, int delay) { (void)ctx; (void)delay; }
static void mipi_dsi_dcs_exit_sleep_mode_multi(struct mipi_dsi_multi_context *ctx) {
	if (!(ctx->dsi->mode_flags & MIPI_DSI_MODE_LPM)) ctx->accum_err = -22;
	commands[count++] = 0x11;
}
static void tx(struct mipi_dsi_multi_context *ctx, const uint8_t *data, size_t size) {
	(void)size;
	if (ctx->accum_err) return;
	/* At streaming video speed, the 32-byte DMA packet cannot fit in LP BLLP. */
	if (ctx->dsi->mode_flags & MIPI_DSI_MODE_LPM) { ctx->accum_err = -110; return; }
	commands[count++] = data[0];
}
#define mipi_dsi_generic_write_seq_multi(ctx, ...) do { const uint8_t b[] = { __VA_ARGS__ }; tx(ctx, b, sizeof(b)); } while (0)
#define mipi_dsi_dcs_write_seq_multi(ctx, ...) mipi_dsi_generic_write_seq_multi(ctx, __VA_ARGS__)
static void mipi_dsi_dcs_set_display_on_multi(struct mipi_dsi_multi_context *ctx) { const uint8_t b[] = { 0x29 }; tx(ctx, b, sizeof(b)); }
static void mipi_dsi_dcs_set_display_off_multi(struct mipi_dsi_multi_context *ctx) { const uint8_t b[] = { 0x28 }; tx(ctx, b, sizeof(b)); }
static void mipi_dsi_dcs_enter_sleep_mode_multi(struct mipi_dsi_multi_context *ctx) { const uint8_t b[] = { 0x10 }; tx(ctx, b, sizeof(b)); }
#define dev_info(...) ((void)0)

/* PANEL_FUNCTIONS */

int main(void)
{
	struct drm_panel panel = { 0 };
	const unsigned expected[] = { 0x11, 0xb0, 0, 0, 0xc7, 0xc8, 0xc9, 0x29, 0x28, 0x10 };
	/* Prepare must restore LP after the previous HS display-off cycle. */
	dsi.mode_flags = 0;
	if (yuga_prepare(&panel)) return 1;
	if (yuga_enable(&panel)) return 2;
	if (yuga_disable(&panel)) return 3;
	if (count != sizeof(expected) / sizeof(expected[0])) return 4;
	for (unsigned i = 0; i < count; i++) if (commands[i] != expected[i]) return 5;
	return 0;
}
