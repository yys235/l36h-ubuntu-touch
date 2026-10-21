#!/usr/bin/env python3
"""Append source-backed Yuga RMI4 wiring; refuse unknown or already wired boards."""
import argparse
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def enable_bus(source):
    if '"sony,xperia-yuga"' not in source or '&gsbi3' in source:
        raise ValueError('Expected original Yuga bus wiring')
    return source + '\n&gsbi3 { qcom,mode = <GSBI_PROT_I2C>; status = "okay"; };\n&gsbi3_i2c { clock-frequency = <400000>; status = "okay"; };\n'


def enable(source):
    if '"sony,xperia-yuga"' not in source:
        raise ValueError('Expected Yuga board')
    if any(token in source for token in ('touchscreen@2c', '&gsbi3')):
        raise ValueError('Touch wiring already present or ambiguous')
    original = '\t\tpm8921_l17: l17 {\n\t\t\tregulator-min-microvolt = <2000000>;\n\t\t\tregulator-max-microvolt = <2000000>;\n\t\t\tbias-pull-down;\n\t\t};'
    if source.count(original) != 1:
        raise ValueError('Unknown touch supply voltage/node')
    source = source.replace(original, original.replace('<2000000>', '<3000000>'))
    return source + '\n' + (HERE/'yuga-touch.dtsi').read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bus-only', action='store_true')
    parser.add_argument('board', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refuse existing output')
    args.output.write_text((enable_bus if args.bus_only else enable)(args.board.read_text()))


if __name__ == '__main__':
    main()
