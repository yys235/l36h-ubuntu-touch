#!/usr/bin/env python3
"""Install the source-backed Yuga display probe into the fixed kernel tree."""
import argparse
import hashlib
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BOARD_PATH = 'arch/arm/boot/dts/qcom/qcom-apq8064-sony-xperia-lagan-yuga.dts'
HOST_PATH = 'drivers/gpu/drm/msm/dsi/dsi_host.c'
MFD_PATH = 'drivers/mfd/lm3533-core.c'
FBDEV_PATH = 'drivers/gpu/drm/msm/msm_fbdev.c'
PHY_PATH = 'drivers/gpu/drm/msm/dsi/phy/dsi_phy_28nm_8960.c'
PINNED = {
    HOST_PATH: '324fea12a3fa5d7a386afb2d0fdfaa20fad93cd8b580196ae1ebf1730781f090',
    MFD_PATH: 'bac2e938de22a2ad5768890fa4049c6f81be0534d2e6c83a34be05340f370ec6',
    FBDEV_PATH: 'd91de279ed7ca5acf65f1f0a8798e8df4ca1fde13a26818239e0f8b7f7970657',
    PHY_PATH: '9a0f5ade2901925b0831895b3273f72e11d8653e3a74f7824847c9dd495350a4',
    'drivers/gpu/drm/panel/Kconfig': '1f610dac5145a51a8b1fb67ed248acef26520e7acb6c3948a54049ea98ed6087',
    'drivers/gpu/drm/panel/Makefile': 'f9f11436eb16a91b82828b59ccdff93e72c241d1cecff986899f684a81ec475c',
}


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unknown or already modified display source anchor')
    return text.replace(old, new)


def enable_board(source):
    if '"sony,xperia-yuga"' not in source or any(
        token in source for token in ('&dsi0', '&mdp', '&gsbi1', 'panel@0', 'backlight@36')
    ):
        raise ValueError('Expected Yuga without existing display wiring')
    supply = '\t\tpm8921_l29: l29 {\n\t\t\tregulator-min-microvolt = <2000000>;\n\t\t\tregulator-max-microvolt = <2000000>;\n\t\t\tbias-pull-down;\n\t\t};'
    source = replace_once(source, supply, supply.replace('<2000000>', '<1800000>'))
    return source + '\n' + (HERE / 'yuga-display.dtsi').read_text()


def patch_host(text):
    text = replace_once(text, 'int msm_dsi_host_init(struct msm_dsi *msm_dsi)',
                        '#include "yuga-dsi-power.h"\n\nint msm_dsi_host_init(struct msm_dsi *msm_dsi)')
    text = replace_once(text, '\tcfg = msm_host->cfg_hnd->cfg;\n',
                        '\tret = yuga_dsi_configure(msm_host);\n\tif (ret)\n\t\treturn ret;\n\tcfg = msm_host->cfg_hnd->cfg;\n')
    text = replace_once(text,
                        '\tret = regulator_bulk_enable(msm_host->cfg_hnd->cfg->num_regulators,\n\t\t\t\t    msm_host->supplies);',
                        '\tret = yuga_dsi_regulators_enable(msm_host);')
    # The panel bring-up diagnostics call the host test-pattern hook from a
    # separate module, so the symbol must be exported.
    text = replace_once(text,
                        '\tif (!is_video_mode)\n\t\tdsi_write(msm_host, REG_DSI_TEST_PATTERN_GEN_CMD_STREAM0_TRIGGER,\n\t\t\t\tDSI_TEST_PATTERN_GEN_CMD_STREAM0_TRIGGER_SW_TRIGGER);\n}',
                        '\tif (!is_video_mode)\n\t\tdsi_write(msm_host, REG_DSI_TEST_PATTERN_GEN_CMD_STREAM0_TRIGGER,\n\t\t\t\tDSI_TEST_PATTERN_GEN_CMD_STREAM0_TRIGGER_SW_TRIGGER);\n}\n\nEXPORT_SYMBOL_GPL(msm_dsi_host_test_pattern_en);')
    # Diagnostic: the panel's DCS read path returns "Invalid response cmd",
    # which hides whether the panel is silent (rx_buf stays zero), replies
    # with an ACK/error packet, or the host mis-parses a valid read response.
    # Dump the raw response bytes so the data type decides the next fix.
    text = replace_once(text,
                        '\tdefault:\n'
                        '\t\tpr_warn("%s:Invalid response cmd\\n", __func__);\n'
                        '\t\tret = 0;\n'
                        '\t}\n'
                        '\n'
                        '\treturn ret;\n'
                        '}',
                        '\tdefault:\n'
                        '\t\tpr_warn("%s:Invalid response cmd dt=0x%02x b1=0x%02x b2=0x%02x b3=0x%02x dlen=%d\\n",\n'
                        '\t\t\t__func__, buf[0], buf[1], buf[2], buf[3], dlen);\n'
                        '\t\tret = 0;\n'
                        '\t}\n'
                        '\n'
                        '\treturn ret;\n'
                        '}')
    # Live-decode the error/timeout state right after a failed RX: without
    # this the only readout path (kms snapshot) does its own pm_runtime
    # get/put and wedges the USB gadget while video streams.
    text = replace_once(text,
                        '\tdefault:\n'
                        '\t\tpr_warn("%s:Invalid response cmd dt=0x%02x b1=0x%02x b2=0x%02x b3=0x%02x dlen=%d\\n",\n'
                        '\t\t\t__func__, buf[0], buf[1], buf[2], buf[3], dlen);\n'
                        '\t\tret = 0;\n'
                        '\t}\n',
                        '\tdefault:\n'
                        '\t\tpr_warn("%s:Invalid response cmd dt=0x%02x b1=0x%02x b2=0x%02x b3=0x%02x dlen=%d\\n",\n'
                        '\t\t\t__func__, buf[0], buf[1], buf[2], buf[3], dlen);\n'
                        '\t\tpr_warn("%s:YUGA ack=0x%08x to=0x%08x lpt=0x%08x hst=0x%08x phy=0x%08x lane=0x%08x fifo=0x%08x\\n",\n'
                        '\t\t\t__func__,\n'
                        '\t\t\tdsi_read(msm_host, REG_DSI_ACK_ERR_STATUS),\n'
                        '\t\t\tdsi_read(msm_host, REG_DSI_TIMEOUT_STATUS),\n'
                        '\t\t\tdsi_read(msm_host, REG_DSI_LP_TIMER_CTRL),\n'
                        '\t\t\tdsi_read(msm_host, REG_DSI_HS_TIMER_CTRL),\n'
                        '\t\t\tdsi_read(msm_host, REG_DSI_DLN0_PHY_ERR),\n'
                        '\t\t\tdsi_read(msm_host, REG_DSI_LANE_STATUS),\n'
                        '\t\t\tdsi_read(msm_host, REG_DSI_FIFO_STATUS));\n'
                        '\t\tret = 0;\n'
                        '\t}\n')
    # Sony sets esc_byte_ratio=9 (byte/9 = 12.47 MHz escape clock). The
    # generic loop picks esc_div=6 (18.7 MHz); the R63311 cannot decode LP
    # packets at that rate, so every panel command was silently ignored
    # (R10/R11: dt=0x00 zeros, panel never left sleep). esc_mhz=13 makes
    # DIV_ROUND_UP(112, 13) = 9, i.e. the legacy divider byte-exact.
    text = replace_once(text,
                        '\tfor (esc_mhz = 20; esc_mhz >= 5; esc_mhz--) {\n',
                        '\t/* Yuga R63311: legacy esc_byte_ratio=9 -> byte/9 =\n'
                        '\t * 12.47 MHz; esc_mhz=13 yields esc_div=9 at the 112 MHz\n'
                        '\t * byte clock. The generic loop picks esc_div=6 (18.7 MHz),\n'
                        '\t * too fast for the panel to decode LP packets. */\n'
                        '\tfor (esc_mhz = 13; esc_mhz >= 5; esc_mhz--) {\n')
    # The R63311 needs the clock lane back in LP-11 between HS bursts: with
    # CLKLN_HS_FORCE_REQUEST latched (R15/R17 measured 0xa8=0x10000000) the
    # host cannot transmit any LP command or BTA, so the panel sees nothing
    # at all. msm_host->mode_flags does not carry the panel's
    # MIPI_DSI_CLOCK_NON_CONTINUOUS, so clear the bit unconditionally here —
    # the legacy 3.4 bring-up never writes it either.
    text = replace_once(text,
                        '\tif (!(flags & MIPI_DSI_CLOCK_NON_CONTINUOUS)) {\n'
                        '\t\tlane_ctrl = dsi_read(msm_host, REG_DSI_LANE_CTRL);\n'
                        '\n'
                        '\t\tif (msm_dsi_phy_set_continuous_clock(phy, true))\n'
                        '\t\t\tlane_ctrl &= ~DSI_LANE_CTRL_HS_REQ_SEL_PHY;\n'
                        '\n'
                        '\t\tdsi_write(msm_host, REG_DSI_LANE_CTRL,\n'
                        '\t\t\tlane_ctrl | DSI_LANE_CTRL_CLKLN_HS_FORCE_REQUEST);\n'
                        '\t}\n',
                        '\tif (!(flags & MIPI_DSI_CLOCK_NON_CONTINUOUS)) {\n'
                        '\t\tlane_ctrl = dsi_read(msm_host, REG_DSI_LANE_CTRL);\n'
                        '\n'
                        '\t\tif (msm_dsi_phy_set_continuous_clock(phy, true))\n'
                        '\t\t\tlane_ctrl &= ~DSI_LANE_CTRL_HS_REQ_SEL_PHY;\n'
                        '\n'
                        '\t\t/* Yuga: leave the clock lane free to fall back to\n'
                        '\t\t * LP-11; forcing HS blocks every LP transfer. */\n'
                        '\t\tdsi_write(msm_host, REG_DSI_LANE_CTRL, lane_ctrl);\n'
                        '\t}\n')
    # Sony R63311 bring-up: mirror the working legacy mipi_dsi_cmds_tx().
    # The legacy driver stops the video engine and sets CMD_MODE_EN for
    # every panel command, because long init sequences cannot fit the
    # BLLP window and the panel fails to decode BLLP-interleaved packets
    # (DCS 0x0A read returns 0 bytes on device; the panel stays black).
    text = replace_once(text,
                        '\tint len, ret;\n\tint bllp_len = msm_host->mode->hdisplay *\n\t\t\tmipi_dsi_pixel_format_to_bpp(msm_host->format) / 8;\n',
                        '\tint len, ret;\n\tint bllp_len = msm_host->mode->hdisplay *\n\t\t\tmipi_dsi_pixel_format_to_bpp(msm_host->format) / 8;\n\tu32 dsi_ctrl_saved = 0;\n\tbool video_switch = false;\n')
    return replace_once(text,
                        '\tret = dsi_cmd_dma_tx(msm_host, len);\n'
                        '\tif (ret < 0) {\n'
                        '\t\tpr_err("%s: cmd dma tx failed, type=0x%x, data0=0x%x, len=%d, ret=%d\\n",\n'
                        '\t\t\t__func__, msg->type, (*(u8 *)(msg->tx_buf)), len, ret);\n'
                        '\t\treturn ret;\n'
                        '\t} else if (ret < len) {\n'
                        '\t\tpr_err("%s: cmd dma tx failed, type=0x%x, data0=0x%x, ret=%d len=%d\\n",\n'
                        '\t\t\t__func__, msg->type, (*(u8 *)(msg->tx_buf)), ret, len);\n'
                        '\t\treturn -EIO;\n'
                        '\t}\n'
                        '\n'
                        '\treturn len;\n'
                        '}',
                        '\tvideo_switch = false;\n'
                        '\tif (msm_host->enabled && (msm_host->mode_flags & MIPI_DSI_MODE_VIDEO)) {\n'
                        '\t\tdsi_ctrl_saved = dsi_read(msm_host, REG_DSI_CTRL);\n'
                        '\t\tdsi_wait4video_eng_busy(msm_host);\n'
                        '\t\tdsi_write(msm_host, REG_DSI_CTRL,\n'
                        '\t\t\t  dsi_ctrl_saved | DSI_CTRL_CMD_MODE_EN);\n'
                        '\t\twmb(); /* command mode latched before the DMA */\n'
                        '\t\tvideo_switch = true;\n'
                        '\t}\n'
                        '\n'
                        '\tret = dsi_cmd_dma_tx(msm_host, len);\n'
                        '\n'
                        '\tif (video_switch) {\n'
                        '\t\twmb();\n'
                        '\t\tdsi_write(msm_host, REG_DSI_CTRL, dsi_ctrl_saved);\n'
                        '\t}\n'
                        '\n'
                        '\tif (ret < 0) {\n'
                        '\t\tpr_err("%s: cmd dma tx failed, type=0x%x, data0=0x%x, len=%d, ret=%d\\n",\n'
                        '\t\t\t__func__, msg->type, (*(u8 *)(msg->tx_buf)), len, ret);\n'
                        '\t\treturn ret;\n'
                        '\t} else if (ret < len) {\n'
                        '\t\tpr_err("%s: cmd dma tx failed, type=0x%x, data0=0x%x, ret=%d len=%d\\n",\n'
                        '\t\t\t__func__, msg->type, (*(u8 *)(msg->tx_buf)), ret, len);\n'
                        '\t\treturn -EIO;\n'
                        '\t}\n'
                        '\n'
                        '\treturn len;\n'
                        '}')


def patch_mfd(text):
    text = replace_once(text, '#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/of.h>')
    text = replace_once(text, 'static int lm3533_device_init(struct lm3533 *lm3533)',
                        '#include "yuga-lm3533.h"\n\nstatic int lm3533_device_init(struct lm3533 *lm3533)')
    text = replace_once(text, '\tlm3533_device_als_init(lm3533);\n\tlm3533_device_bl_init(lm3533);',
                        '\tret = lm3533_yuga_outputs(lm3533);\n\tif (ret)\n\t\tgoto err_disable;\n\tlm3533_device_als_init(lm3533);\n\tret = lm3533_device_bl_init(lm3533);\n\tif (ret)\n\t\tgoto err_unregister;')
    text = replace_once(text, '\treturn lm3533_device_init(lm3533);',
                        '\t{\n\t\tint ret = lm3533_yuga_platform_data(&i2c->dev);\n\t\tif (ret)\n\t\t\treturn ret;\n\t}\n\treturn lm3533_device_init(lm3533);')
    text = replace_once(text, 'static struct i2c_driver lm3533_i2c_driver = {',
                        'static const struct of_device_id lm3533_yuga_of_match[] = {\n\t{ .compatible = "sony,yuga-lm3533" }, { }\n};\nMODULE_DEVICE_TABLE(of, lm3533_yuga_of_match);\n\nstatic struct i2c_driver lm3533_i2c_driver = {')
    return replace_once(text, '\t\t   .name = "lm3533",',
                        '\t\t   .name = "lm3533",\n\t\t   .of_match_table = lm3533_yuga_of_match,')


def patch_fbdev(text):
    # The 2025 fbdev core sys_* blit helpers warn once and callers may treat
    # the warning as failure evidence; the msm fbdev backing store is a
    # vmapped GEM buffer accessed through screen_buffer, so mark it virtual.
    # The anchor includes the following blank line so re-application refuses
    # instead of inserting the flag twice.
    return replace_once(text, '\tfbi->fbops = &msm_fb_ops;\n\n',
                        '\tfbi->fbops = &msm_fb_ops;\n\tfbi->flags |= FBINFO_VIRTFB;\n\n')


def patch_phy(text):
    # Sony's panel-specific PHY db tunes the data-lane HS timing to 0xef
    # (mipi_dsi_panel_r63311_sharp_ls050t3sx01.c dsi_video_mode_phy_db);
    # the generic upstream value 0x45 leaves the panel unable to decode HS
    # packets: host TX completes but the panel never ACKs or displays.
    text = replace_once(text,
                        'writel(0x45, base + REG_DSI_28nm_8960_PHY_LN_CFG_1(i));',
                        'writel(0xef, base + REG_DSI_28nm_8960_PHY_LN_CFG_1(i));')
    # Replace the computed D-PHY timings with the complete Sony panel table
    # {e6,38,27,00,69,72,2b,3c,41,03,04,a0} so the whole PHY matches the
    # working legacy configuration exactly.
    return replace_once(text,
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_0_CLK_ZERO(timing->clk_zero),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_0);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_1_CLK_TRAIL(timing->clk_trail),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_1);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_2_CLK_PREPARE(timing->clk_prepare),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_2);\n'
                        '	writel(0, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_3);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_4_HS_EXIT(timing->hs_exit),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_4);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_5_HS_ZERO(timing->hs_zero),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_5);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_6_HS_PREPARE(timing->hs_prepare),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_6);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_7_HS_TRAIL(timing->hs_trail),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_7);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_8_HS_RQST(timing->hs_rqst),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_8);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_9_TA_GO(timing->ta_go) |\n'
                        '	       DSI_28nm_8960_PHY_TIMING_CTRL_9_TA_SURE(timing->ta_sure),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_9);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_10_TA_GET(timing->ta_get),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_10);\n'
                        '	writel(DSI_28nm_8960_PHY_TIMING_CTRL_11_TRIG3_CMD(0),\n'
                        '	       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_11);\n',
                        '	writel(0xe6, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_0);\n'
                        '	writel(0x38, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_1);\n'
                        '	writel(0x27, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_2);\n'
                        '	writel(0x00, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_3);\n'
                        '	writel(0x69, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_4);\n'
                        '	writel(0x72, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_5);\n'
                        '	writel(0x2b, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_6);\n'
                        '	writel(0x3c, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_7);\n'
                        '	writel(0x41, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_8);\n'
                        '	writel(0x03, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_9);\n'
                        '	writel(0x04, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_10);\n'
                        '	writel(0xa0, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_11);\n')


def install(root):
    root = pathlib.Path(root)
    if root.is_symlink() or root.resolve() == pathlib.Path(root.anchor):
        raise ValueError('Unsafe kernel source root')
    pending = {}
    try:
        for name, digest in PINNED.items():
            path = root / name
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Unknown display source revision: ' + name)
            pending[name] = path.read_text()
        pending[BOARD_PATH] = enable_board((root / BOARD_PATH).read_text())
        pending[HOST_PATH] = patch_host(pending[HOST_PATH])
        pending[MFD_PATH] = patch_mfd(pending[MFD_PATH])
        pending[FBDEV_PATH] = patch_fbdev(pending[FBDEV_PATH])
        pending[PHY_PATH] = patch_phy(pending[PHY_PATH])
        pending['drivers/gpu/drm/panel/Kconfig'] += '\nconfig DRM_PANEL_SHARP_LS050T3SX01\n\ttristate "Sharp LS050T3SX01 Sony Yuga diagnostic panel"\n\tdepends on OF && DRM_MIPI_DSI && BACKLIGHT_CLASS_DEVICE\n\thelp\n\t  Source-backed R63311 panel bring-up for Sony Xperia Z.\n'
        pending['drivers/gpu/drm/panel/Makefile'] += '\nobj-$(CONFIG_DRM_PANEL_SHARP_LS050T3SX01) += panel-sharp-ls050t3sx01.o\n'
        for name, source in {
            'drivers/gpu/drm/panel/panel-sharp-ls050t3sx01.c': 'panel-sharp-ls050t3sx01.c',
            'drivers/gpu/drm/msm/dsi/yuga-dsi-power.h': 'yuga-dsi-power.h',
            'drivers/mfd/yuga-lm3533.h': 'yuga-lm3533.h',
        }.items():
            if (root / name).exists():
                raise ValueError('Refuse existing display integration')
            pending[name] = (HERE / source).read_text()
        for name in pending:
            if not (root / name).resolve().is_relative_to(root.resolve()):
                raise ValueError('Display source path escapes kernel tree')
    except (FileNotFoundError, NotADirectoryError) as error:
        raise ValueError('Incomplete fixed kernel source tree') from error
    # Validate every source and destination before changing any file.
    for name, text in pending.items():
        (root / name).write_bytes(text.encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=pathlib.Path)
    install(parser.parse_args().source)
