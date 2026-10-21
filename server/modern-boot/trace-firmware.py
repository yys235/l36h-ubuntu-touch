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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=pathlib.Path)
    args = parser.parse_args()
    path = args.source / 'drivers/soc/qcom/mdt_loader.c'
    path.write_text(instrument(path.read_text()))


if __name__ == '__main__':
    main()
