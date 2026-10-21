import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / 'trace-firmware.py'
CALLS = [
    'ret = qcom_mdt_load(wcnss->dev, fw, rproc->firmware, WCNSS_PAS_ID,\n'
    '\t\t\t    wcnss->mem_region, wcnss->mem_phys,\n'
    '\t\t\t    wcnss->mem_size, &wcnss->mem_reloc);',
    'ret = regulator_bulk_enable(wcnss->num_vregs, wcnss->vregs);',
    'ret = qcom_iris_enable(wcnss->iris);',
    'wcnss_configure_iris(wcnss);',
    'ret = qcom_scm_pas_auth_and_reset(WCNSS_PAS_ID);',
    'qcom_iris_disable(wcnss->iris);',
    'regulator_bulk_disable(wcnss->num_vregs, wcnss->vregs);',
]


class WcnssTrace(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('trace', PATH)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.source = '\n'.join('\t' + call for call in CALLS) + '\n'

    def test_call_order_and_results_preserved(self):
        result = self.mod.instrument_wcnss(self.source)
        previous = -1
        for call in CALLS:
            self.assertEqual(result.count(call), 1)
            position = result.index(call)
            self.assertGreater(position, previous)
            previous = position
        for stage in ['mdt_load', 'regulator_enable', 'iris_enable',
                      'iris_configure', 'auth_reset', 'iris_disable',
                      'regulator_disable']:
            self.assertEqual(result.count(stage + ' begin'), 1)
        self.assertIn('auth_reset end ret=%d', result)
        self.assertNotIn('return 0;', result)

    def test_unknown_duplicate_and_reapplication_fail_closed(self):
        for source in ['', self.source + '\twcnss_configure_iris(wcnss);\n']:
            with self.assertRaises(ValueError):
                self.mod.instrument_wcnss(source)
        with self.assertRaises(ValueError):
            self.mod.instrument_wcnss(self.mod.instrument_wcnss(self.source))
