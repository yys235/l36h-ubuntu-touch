#!/usr/bin/env python3
"""Trace the RMI IRQ/configuration boundary without changing its call order."""
import argparse
import pathlib


def instrument(source):
    if 'YUGA_RMI_TRACE' in source:
        raise ValueError('RMI trace already applied')
    sites = [
        ('irq_init', 'retval = rmi_irq_init(rmi_dev);'),
        ('process_config', 'retval = rmi_driver_process_config_requests(rmi_dev);'),
        ('process_interrupts', 'return rmi_process_interrupt_requests(rmi_dev);'),
    ]
    for stage, call in sites:
        exact = '\t' + call + '\n'
        if source.count(exact) != 1:
            raise ValueError('Expected exactly one RMI call: ' + stage)
        before = '\tdev_info(&rmi_dev->dev, "YUGA_RMI_TRACE ' + stage + ' begin\\n");\n'
        after = '\tdev_info(&rmi_dev->dev, "YUGA_RMI_TRACE ' + stage + ' end ret=%d\\n", retval);\n'
        invocation = exact.replace('return ', 'retval = ') if call.startswith('return ') else exact
        tail = '\treturn retval;\n' if call.startswith('return ') else ''
        source = source.replace(exact, before + invocation + after + tail)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=pathlib.Path)
    args = parser.parse_args()
    path = args.source / 'drivers/input/rmi4/rmi_driver.c'
    path.write_bytes(instrument(path.read_text()).encode())


if __name__ == '__main__':
    main()
