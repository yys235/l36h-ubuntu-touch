#!/usr/bin/env python3
"""Fix the diagnostic USB role without requiring unsupported OTG-ID detection."""
import pathlib
import sys


def peripheral_role(source):
    expected = '&usb1 {\n\tdr_mode = "otg";\n\tstatus = "okay";\n};'
    if source.count(expected) != 1:
        raise ValueError('expected exactly one original Yuga USB1 node')
    return source.replace(expected, expected.replace('"otg"', '"peripheral"'))


def card_detect_pinconf(source):
    expected = '\tsdcc3_cd_pin_a: sdcc3-cd-pin-active-state {\n\t\tpins = "gpio26";\n\t\tfunction = "gpio";'
    if source.count(expected) != 1:
        raise ValueError('expected exactly one original Yuga card-detect GPIO26 node')
    # GPIO descriptor acquisition selects the mux. Claim only electrical pinconf
    # here, otherwise strict pin ownership rejects the subsequent GPIO request.
    return source.replace(expected, expected.removesuffix('\n\t\tfunction = "gpio";'))


if __name__ == '__main__':
    path = pathlib.Path(sys.argv[1]) / 'arch/arm/boot/dts/qcom/qcom-apq8064-sony-xperia-lagan-yuga.dts'
    path.write_text(card_detect_pinconf(peripheral_role(path.read_text())))
