#!/usr/bin/env python3
"""Fix the diagnostic USB role without requiring unsupported OTG-ID detection."""
import pathlib
import sys


def peripheral_role(source):
    expected = '&usb1 {\n\tdr_mode = "otg";\n\tstatus = "okay";\n};'
    if source.count(expected) != 1:
        raise ValueError('expected exactly one original Yuga USB1 node')
    return source.replace(expected, expected.replace('"otg"', '"peripheral"'))


if __name__ == '__main__':
    path = pathlib.Path(sys.argv[1]) / 'arch/arm/boot/dts/qcom/qcom-apq8064-sony-xperia-lagan-yuga.dts'
    path.write_text(peripheral_role(path.read_text()))
