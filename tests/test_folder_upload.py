"""Integridade e isolamento das pastas enviadas pelo navegador."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from folder_upload import FolderUploads, relative_name


class FolderUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.api=FolderUploads(self.root)

    def start(self, path='sub/acentuação.png', raw=b'unchanged bytes'):
        return self.api.start('Amostras', [{'path':path,'bytes':len(raw)}])['id']

    def test_nested_files_and_bytes_preserved_after_finish(self):
        raw=b'original\x00\xff\x89bytes';name='sub/acentuação.png'
        ident=self.start(name,raw)
        self.api.put(ident,name,raw)
        result=self.api.finish(ident)
        folder=Path(result['folder'])
        self.assertEqual((folder/name).read_bytes(),raw)
        self.assertEqual(result['label'],'Amostras')
        record=json.loads((folder/'origem_navegador.json').read_text(encoding='utf-8'))
        self.assertEqual(record['files'][0]['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertFalse(self.api.cancel(ident)['cancelled'])
        self.assertTrue(folder.exists())

    def test_cancel_removes_only_this_pending_selection(self):
        sentinel=self.root/'imagem_original.png';sentinel.write_bytes(b'original')
        first=self.start();second=self.start()
        folder=self.api.pending[first]['folder']
        self.api.put(first,'sub/acentuação.png',b'unchanged bytes')
        self.assertTrue(self.api.cancel(first)['cancelled'])
        self.assertFalse(folder.exists())
        self.assertTrue(self.api.pending[second]['folder'].is_dir())
        self.assertEqual(sentinel.read_bytes(),b'original')
        self.assertFalse(self.api.cancel('unknown')['cancelled'])

    def test_finish_requires_all_files_and_exact_sizes(self):
        ident=self.start()
        with self.assertRaises(ValueError):self.api.finish(ident)
        with self.assertRaises(ValueError):self.api.put(ident,'sub/acentuação.png',b'truncated')
        with self.assertRaises(ValueError):self.api.put(ident,'other.png',b'unchanged bytes')
        self.api.put(ident,'sub/acentuação.png',b'unchanged bytes')
        with self.assertRaises(ValueError):self.api.put(ident,'sub/acentuação.png',b'unchanged bytes')
        self.assertEqual(self.api.finish(ident)['count'],1)

    def test_paths_cannot_escape_or_target_windows_devices(self):
        for name in ('../x.png','/x.png','a/../x.png','a//x.png','a\\x.png','Z:/x.png',
                     'x.png:stream','NUL.png','a/COM1.png','a./x.png','x.png ','x\x00.png','a.txt'):
            with self.subTest(name=name),self.assertRaises(ValueError):relative_name(name)
        self.assertEqual(relative_name('sub pasta/imagem.JPG'),'sub pasta/imagem.JPG')

    def test_duplicate_names_and_limits_before_writing(self):
        invalid=[[],[{'path':'A.png','bytes':1},{'path':'a.png','bytes':1}],
                 [{'path':'a.png','bytes':20_000_001}],[{'path':'a.png','bytes':True}]]
        for files in invalid:
            with self.subTest(files=files),self.assertRaises(ValueError):self.api.start('Amostras',files)
        self.assertFalse(self.api.root.exists())

    def test_insufficient_space_does_not_create_an_upload(self):
        usage=shutil.disk_usage(self.root)
        with patch('folder_upload.shutil.disk_usage',return_value=type(usage)(usage.total,usage.used,0)):
            with self.assertRaisesRegex(ValueError,'espaço'):self.start()
        self.assertEqual(list(self.api.root.iterdir()),[])


if __name__=='__main__':unittest.main()
