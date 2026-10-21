#!/usr/bin/env python3
"""Add bounded diagnostic messages around firmware secure monitor calls."""
import argparse
import pathlib


def instrument(source):
    sites = [
        ('\t', 'pas_init_image', 'ret = qcom_scm_pas_init_image(pas_id, metadata, metadata_len, ctx);'),
        ('\t\t', 'pas_mem_setup', 'ret = qcom_scm_pas_mem_setup(pas_id, mem_phys, max_addr - min_addr);'),
    ]
    if 'YUGA_MDT_TRACE' in source:
        raise ValueError('Firmware trace already applied')
    for indent, stage, call in sites:
        exact = indent + call + '\n'
        if source.count(exact) != 1:
            raise ValueError('Expected exactly one secure firmware call: ' + stage)
        before = indent + 'dev_info(dev, "YUGA_MDT_TRACE ' + stage + ' begin id=%u\\n", pas_id);\n'
        after = indent + 'dev_info(dev, "YUGA_MDT_TRACE ' + stage + ' end ret=%d\\n", ret);\n'
        source = source.replace(exact, before + exact + after)
    return source


def instrument_wcnss(source):
    if 'YUGA_WCNSS_TRACE' in source:
        raise ValueError('WCNSS trace already applied')
    sites = [
        ('mdt_load', 'ret = qcom_mdt_load(wcnss->dev, fw, rproc->firmware, WCNSS_PAS_ID,\n'
         '\t\t\t    wcnss->mem_region, wcnss->mem_phys,\n'
         '\t\t\t    wcnss->mem_size, &wcnss->mem_reloc);', True),
        ('regulator_enable', 'ret = regulator_bulk_enable(wcnss->num_vregs, wcnss->vregs);', True),
        ('iris_enable', 'ret = qcom_iris_enable(wcnss->iris);', True),
        ('iris_configure', 'wcnss_configure_iris(wcnss);', False),
        ('auth_reset', 'ret = qcom_scm_pas_auth_and_reset(WCNSS_PAS_ID);', True),
        ('iris_disable', 'qcom_iris_disable(wcnss->iris);', False),
        ('regulator_disable', 'regulator_bulk_disable(wcnss->num_vregs, wcnss->vregs);', False),
    ]
    for stage, call, returns_int in sites:
        exact = '\t' + call + '\n'
        if source.count(exact) != 1:
            raise ValueError('Expected exactly one WCNSS call: ' + stage)
        before = '\tdev_info(wcnss->dev, "YUGA_WCNSS_TRACE ' + stage + ' begin\\n");\n'
        if returns_int:
            after = '\tdev_info(wcnss->dev, "YUGA_WCNSS_TRACE ' + stage + ' end ret=%d\\n", ret);\n'
        else:
            after = '\tdev_info(wcnss->dev, "YUGA_WCNSS_TRACE ' + stage + ' end\\n");\n'
        source = source.replace(exact, before + exact + after)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=pathlib.Path)
    args = parser.parse_args()
    path = args.source / 'drivers/soc/qcom/mdt_loader.c'
    path.write_text(instrument(path.read_text()))
    path = args.source / 'drivers/remoteproc/qcom_wcnss.c'
    path.write_text(instrument_wcnss(path.read_text()))


if __name__ == '__main__':
    main()
