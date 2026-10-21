import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / 'trace-touch.py'
SOURCE = '\tretval = rmi_irq_init(rmi_dev);\n\tretval = rmi_driver_process_config_requests(rmi_dev);\n\treturn rmi_process_interrupt_requests(rmi_dev);\n'

class TouchTrace(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('touch_trace', PATH)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_each_call_executes_once_and_final_result_is_returned(self):
        result = self.mod.instrument(SOURCE)
        for call in ['rmi_irq_init(rmi_dev)', 'rmi_driver_process_config_requests(rmi_dev)', 'rmi_process_interrupt_requests(rmi_dev)']:
            self.assertEqual(result.count(call), 1)
        self.assertTrue(result.endswith('\treturn retval;\n'))
        for stage in ['irq_init', 'process_config', 'process_interrupts']:
            self.assertEqual(result.count(stage + ' begin'), 1)
            self.assertEqual(result.count(stage + ' end'), 1)

    def test_already_instrumented_source_refused(self):
        with self.assertRaises(ValueError):
            self.mod.instrument(self.mod.instrument(SOURCE))

    def test_missing_or_duplicate_call_refused(self):
        for source in ['', SOURCE + SOURCE]:
            with self.assertRaises(ValueError):
                self.mod.instrument(source)
