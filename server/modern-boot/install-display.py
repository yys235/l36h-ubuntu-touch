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
PINNED = {
    HOST_PATH: '324fea12a3fa5d7a386afb2d0fdfaa20fad93cd8b580196ae1ebf1730781f090',
    MFD_PATH: 'bac2e938de22a2ad5768890fa4049c6f81be0534d2e6c83a34be05340f370ec6',
    FBDEV_PATH: 'd91de279ed7ca5acf65f1f0a8798e8df4ca1fde13a26818239e0f8b7f7970657',
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
    return replace_once(text,
                        '\tret = regulator_bulk_enable(msm_host->cfg_hnd->cfg->num_regulators,\n\t\t\t\t    msm_host->supplies);',
                        '\tret = yuga_dsi_regulators_enable(msm_host);')


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
