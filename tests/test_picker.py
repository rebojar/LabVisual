"""Contratos do seletor, sem abrir janelas nem executar o encoder."""
from pathlib import Path
from unittest.mock import patch
import builtins
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import picker_dialog
import picker_service


class PickerTests(unittest.TestCase):
    def test_isolated_desktop_does_not_open_an_invisible_dialog(self):
        with patch.object(picker_dialog, 'interactive_desktop', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'Abrir_bancada.cmd'):
                picker_dialog.choose_windows('')
        with patch.object(picker_service, 'interactive_desktop', return_value=False):
            with patch.object(picker_service.subprocess, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'Abrir_bancada.cmd'):
                    picker_service.choose('')
                run.assert_not_called()

    def test_windows_module_does_not_need_tkinter(self):
        original = builtins.__import__
        def without_tk(name, *args, **kwargs):
            if name.startswith(('tkinter', '_tkinter')):
                raise ImportError('Tcl/Tk indisponível neste ambiente de teste')
            return original(name, *args, **kwargs)
        spec = importlib.util.spec_from_file_location('isolated_picker', ROOT/'picker_dialog.py')
        module = importlib.util.module_from_spec(spec)
        with patch('builtins.__import__', side_effect=without_tk):
            spec.loader.exec_module(module)
        self.assertEqual(module.dialog_result(None), {'cancelled': True, 'folder': None})

    def test_folder_contract_unicode_and_existing_directory(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)/"imagens com acentuação e 'aspas'"
            folder.mkdir()
            self.assertEqual(picker_dialog.dialog_result(str(folder)),
                             {'cancelled': False, 'folder': str(folder.resolve())})
            file = folder/'arquivo.txt'
            file.write_text('não é uma pasta', encoding='utf-8')
            with self.assertRaises(ValueError): picker_dialog.dialog_result(str(file))
            with self.assertRaises(ValueError): picker_dialog.dialog_result(str(folder/'ausente'))

    def test_hresult_preserves_windows_errors(self):
        for ok in (0, 1): picker_dialog.check_hresult(ok, 'Operação')
        for error in (0x80004005, -2147467259):
            with self.assertRaisesRegex(RuntimeError, '80004005'):
                picker_dialog.check_hresult(error, 'Operação')

    def test_service_preserves_cancel_and_unicode(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)/'acentuação'; folder.mkdir()
            for result in ({'cancelled': True, 'folder': None},
                           {'cancelled': False, 'folder': str(folder)}):
                completed = subprocess.CompletedProcess([], 0, json.dumps(result, ensure_ascii=False), '')
                with patch.object(picker_service, 'interactive_desktop', return_value=True), \
                        patch.object(picker_service.subprocess, 'run', return_value=completed) as run:
                    self.assertEqual(picker_service.choose(str(folder)), result)
                    args, kwargs = run.call_args
                    self.assertEqual(args[0][-1], str(folder))
                    self.assertFalse(kwargs.get('shell', False))
                    self.assertEqual(kwargs['encoding'], 'utf-8')

    def test_service_keeps_diagnostic_local(self):
        failed = subprocess.CompletedProcess([], 1, '', 'detalhe técnico para o log')
        with patch.object(picker_service, 'interactive_desktop', return_value=True), \
                patch.object(picker_service.subprocess, 'run', return_value=failed):
            with self.assertLogs(level='ERROR') as messages:
                with self.assertRaises(RuntimeError) as error:
                    picker_service.choose('')
        self.assertIn('detalhe técnico', messages.output[0])
        self.assertNotIn('detalhe técnico', str(error.exception))


if __name__ == '__main__':
    unittest.main()
