import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / 'trace-firmware.py'

class FirmwareTrace(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('firmware_trace', PATH)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_scm_calls_preserved_with_before_after_markers(self):
        source = '\tret = qcom_scm_pas_init_image(pas_id, metadata, metadata_len, ctx);\n\t\tret = qcom_scm_pas_mem_setup(pas_id, mem_phys, max_addr - min_addr);\n'
        result = self.mod.instrument(source)
        for call in source.splitlines():
            self.assertEqual(result.count(call), 1)
        for stage in ['pas_init_image begin', 'pas_init_image end', 'pas_mem_setup begin', 'pas_mem_setup end']:
            self.assertEqual(result.count(stage), 1)
        self.assertLess(result.index('pas_init_image begin'), result.index('ret = qcom_scm_pas_init_image'))
        self.assertGreater(result.index('pas_init_image end'), result.index('ret = qcom_scm_pas_init_image'))

    def test_unknown_or_duplicate_source_rejected(self):
        for source in ['', '\tret = qcom_scm_pas_init_image(pas_id, metadata, metadata_len, ctx);\n' * 2]:
            with self.assertRaises(ValueError):
                self.mod.instrument(source)
