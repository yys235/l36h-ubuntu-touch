import importlib.util
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
BOARD = '/ { compatible = "sony,xperia-yuga", "qcom,apq8064"; };\n' + '\t\tpm8921_l29: l29 {\n\t\t\tregulator-min-microvolt = <2000000>;\n\t\t\tregulator-max-microvolt = <2000000>;\n\t\t\tbias-pull-down;\n\t\t};\n'


class Display(unittest.TestCase):
    def setUp(self):
        path = HERE / 'install-display.py'
        self.assertTrue(path.exists(), 'modern Yuga display source integration is missing')
        spec = importlib.util.spec_from_file_location('display', path)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_only_display_supply_and_graph_added(self):
        result = self.mod.enable_board(BOARD)
        self.assertTrue(result.startswith(BOARD.replace('<2000000>', '<1800000>')))
        self.assertIn('compatible = "sharp,ls050t3sx01"', result)
        self.assertIn('reset-gpios = <&pm8921_gpio 25 GPIO_ACTIVE_LOW>', result)
        self.assertIn('dcdc-en-gpios = <&pm8921_gpio 24 GPIO_ACTIVE_HIGH>', result)
        self.assertIn('gpios = <&pm8921_gpio 26 GPIO_ACTIVE_HIGH>', result)
        self.assertIn('vddio-supply = <&pm8921_l29>', result)
        self.assertIn('vdda-supply = <&pm8921_l2>', result)
        self.assertNotIn('avdd-supply', result)
        self.assertNotIn('pm8921_lvs7', result)

    def test_unknown_board_voltage_or_existing_wiring_refused(self):
        for source in [BOARD.replace('xperia-yuga', 'xperia-odin'),
                       BOARD.replace('<2000000>', '<2800000>'),
                       BOARD + '&dsi0 {};', BOARD + '&gsbi1 {};',
                       BOARD + 'panel@0 {};', BOARD + '&mdp {};']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.mod.enable_board(source)

    def test_fbdev_marks_backing_store_virtual_exactly_once(self):
        sample = ('\tstruct fb_info *fbi = helper->info;\n'
                  '\tfbi->fbops = &msm_fb_ops;\n\n'
                  '\tdrm_fb_helper_fill_info(fbi, helper, sizes);\n')
        patched = self.mod.patch_fbdev(sample)
        self.assertIn('\tfbi->fbops = &msm_fb_ops;\n\tfbi->flags |= FBINFO_VIRTFB;\n\n', patched)
        self.assertEqual(patched.count('FBINFO_VIRTFB'), 1)
        self.assertTrue(patched.startswith(sample[:sample.index('\tfbi->fbops')]))
        self.assertIn('\tfbi->flags |= FBINFO_VIRTFB;\n\n\tdrm_fb_helper_fill_info', patched)
        with self.assertRaises(ValueError):
            self.mod.patch_fbdev(patched)

    def test_fbdev_unknown_source_rejected(self):
        for source in ['\tfbi->fbops = &other_ops;\n', '', '\tfbi->flags |= FBINFO_VIRTFB;\n']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.mod.patch_fbdev(source)

    def test_host_patch_exports_test_pattern_hook(self):
        sample = ('int msm_dsi_host_init(struct msm_dsi *msm_dsi)\n{\n'
                  '\tcfg = msm_host->cfg_hnd->cfg;\n'
                  '\tret = regulator_bulk_enable(msm_host->cfg_hnd->cfg->num_regulators,\n'
                  '\t\t\t\t    msm_host->supplies);\n'
                  '\tif (!is_video_mode)\n'
                  '\t\tdsi_write(msm_host, REG_DSI_TEST_PATTERN_GEN_CMD_STREAM0_TRIGGER,\n'
                  '\t\t\t\tDSI_TEST_PATTERN_GEN_CMD_STREAM0_TRIGGER_SW_TRIGGER);\n'
                  '}\n'
                  '\tdefault:\n'
                  '\t\tpr_warn("%s:Invalid response cmd\\n", __func__);\n'
                  '\t\tret = 0;\n'
                  '\t}\n'
                  '\n'
                  '\treturn ret;\n'
                  '}\n'
                  '\tbyte_mhz = msm_host->byte_clk_rate / 1000000;\n'
                  '\n'
                  '\tfor (esc_mhz = 20; esc_mhz >= 5; esc_mhz--) {\n'
                  '\tint len, ret;\n'
                  '\tint bllp_len = msm_host->mode->hdisplay *\n'
                  '\t\t\tmipi_dsi_pixel_format_to_bpp(msm_host->format) / 8;\n'
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
                  '}\n')
        patched = self.mod.patch_host(sample)
        self.assertIn('EXPORT_SYMBOL_GPL(msm_dsi_host_test_pattern_en);', patched)
        self.assertIn('Invalid response cmd dt=0x%02x b1=0x%02x b2=0x%02x b3=0x%02x dlen=%d', patched)
        self.assertIn('for (esc_mhz = 13; esc_mhz >= 5; esc_mhz--) {', patched)
        self.assertIn('esc_byte_ratio=9', patched)
        self.assertIn('u32 dsi_ctrl_saved = 0;', patched)
        self.assertIn('bool video_switch = false;', patched)
        self.assertIn('dsi_ctrl_saved | DSI_CTRL_CMD_MODE_EN', patched)
        self.assertIn('\tif (video_switch) {', patched)
        with self.assertRaises(ValueError):
            self.mod.patch_host(patched)

    def test_phy_lane_timing_uses_sony_panel_tuned_value(self):
        sample = ('writel(0x45, base + REG_DSI_28nm_8960_PHY_LN_CFG_1(i));\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_0_CLK_ZERO(timing->clk_zero),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_0);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_1_CLK_TRAIL(timing->clk_trail),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_1);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_2_CLK_PREPARE(timing->clk_prepare),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_2);\n'
                  '\twritel(0, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_3);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_4_HS_EXIT(timing->hs_exit),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_4);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_5_HS_ZERO(timing->hs_zero),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_5);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_6_HS_PREPARE(timing->hs_prepare),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_6);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_7_HS_TRAIL(timing->hs_trail),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_7);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_8_HS_RQST(timing->hs_rqst),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_8);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_9_TA_GO(timing->ta_go) |\n'
                  '\t       DSI_28nm_8960_PHY_TIMING_CTRL_9_TA_SURE(timing->ta_sure),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_9);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_10_TA_GET(timing->ta_get),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_10);\n'
                  '\twritel(DSI_28nm_8960_PHY_TIMING_CTRL_11_TRIG3_CMD(0),\n'
                  '\t       base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_11);\n')
        patched = self.mod.patch_phy(sample)
        self.assertIn('writel(0xef, base + REG_DSI_28nm_8960_PHY_LN_CFG_1(i));', patched)
        self.assertIn('writel(0xe6, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_0);', patched)
        self.assertIn('writel(0xa0, base + REG_DSI_28nm_8960_PHY_TIMING_CTRL_11);', patched)
        self.assertNotIn('0x45', patched)
        self.assertNotIn('timing->clk_zero', patched)
        with self.assertRaises(ValueError):
            self.mod.patch_phy(patched)

    def test_phy_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            self.mod.patch_phy('writel(0x44, base + REG_DSI_28nm_8960_PHY_LN_CFG_1(i));\n')

    def test_unknown_source_rejected_without_partial_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            board = root / self.mod.BOARD_PATH
            board.parent.mkdir(parents=True)
            board.write_text(BOARD)
            with self.assertRaises(ValueError):
                self.mod.install(root)
            self.assertEqual(board.read_text(), BOARD)
            self.assertFalse((root / 'drivers/gpu/drm/panel/panel-sharp-ls050t3sx01.c').exists())

    @unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
    def test_lm3533_board_register_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / 'lm3533-contract'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(HERE / 'tests/test_lm3533_board.c'), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)])
            self.assertEqual(result.returncode, 0, 'LM3533 Sony board register contract failed')

    @unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
    def test_dsi_rail_order_and_failure_unwind_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / 'dsi-contract'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(HERE / 'tests/test_dsi_power.c'), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)])
            self.assertEqual(result.returncode, 0, 'DSI Sony rail sequencing contract failed')

    def test_native_clock_fits_observed_pll_and_pixel_divider_tolerance(self):
        source = (HERE / 'panel-sharp-ls050t3sx01.c').read_text()
        clock_khz = int(re.search(r'\.clock\s*=\s*(\d+)', source)[1])
        # Measured PLL=898 MHz, DIV3=2. Pixel RCG allows parent error <=100 kHz.
        self.assertLessEqual(abs(clock_khz * 1000 * 3 - 449000000), 100000)

    def test_bringup_diagnostics_wired_to_dsi_device(self):
        source = (HERE / 'panel-sharp-ls050t3sx01.c').read_text()
        self.assertIn('static DEVICE_ATTR_WO(yuga_test);', source)
        self.assertIn('device_create_file(&dsi->dev, &dev_attr_yuga_test)', source)
        self.assertIn('device_remove_file(&dsi->dev, &dev_attr_yuga_test)', source)
        for op in ['sysfs_streq(buf, "on")', 'sysfs_streq(buf, "read")',
                   'sysfs_streq(buf, "tpg")']:
            self.assertIn(op, source)
        self.assertIn('msm_dsi_host_test_pattern_en(dsi->host)', source)
        self.assertIn('mipi_dsi_dcs_read(dsi, MIPI_DCS_GET_POWER_MODE', source)

    def test_ramoops_reserved_for_crash_logs(self):
        source = (HERE / 'yuga-display.dtsi').read_text()
        self.assertIn('ramoops@bf000000', source)
        self.assertIn('compatible = "ramoops";', source)
        self.assertIn('reg = <0xbf000000 0x100000>;', source)
        self.assertIn('no-map;', source)
        # Top of the 2 GiB bank: clear of smem@80000000, wcnss@8f000000 and
        # the peripheral VM area; must not collide with either.
        for taken in ('0x80000000', '0x8f000000', '0xbf0', '0xc0000000'):
            self.assertNotIn('reg = <' + taken, source.replace(
                'reg = <0xbf000000 0x100000>;', ''))

    @unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
    def test_actual_panel_callbacks_use_lp_prepare_and_hs_video_commands(self):
        source = (HERE / 'panel-sharp-ls050t3sx01.c').read_text()
        functions = []
        for name in ['yuga_prepare', 'yuga_enable', 'yuga_disable']:
            start = source.index('static int ' + name + '(')
            first = source.index('{', start)
            depth = 1
            end = first + 1
            while depth:
                depth += (source[end] == '{') - (source[end] == '}')
                end += 1
            functions.append(source[start:end])
        template = (HERE / 'tests/test_panel_transfer.c').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            program = pathlib.Path(tmp) / 'panel-transfer.c'
            program.write_text(template.replace('/* PANEL_FUNCTIONS */', '\n\n'.join(functions)))
            binary = pathlib.Path(tmp) / 'panel-transfer'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(program), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)])
            self.assertEqual(result.returncode, 0, 'Sony LP/HS panel callback contract failed')


if __name__ == '__main__':
    unittest.main()
