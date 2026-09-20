"""Regressões de privacidade da seleção pública, sem modelo ou rede."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_gate", SOURCE / "tools/check_publication_gate.py")
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lab-package-test-")
        self.root = Path(self.temp.name).resolve() / "candidate"
        manifest = json.loads((SOURCE / "code_manifest.json").read_text(encoding="utf-8"))
        for name in [*manifest["files"], "code_manifest.json"]:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / name, destination)
        self.old_root, self.old_self = gate.ROOT, gate.SELF
        gate.ROOT = self.root
        gate.SELF = self.root / "tools/check_publication_gate.py"

    def tearDown(self):
        gate.ROOT, gate.SELF = self.old_root, self.old_self
        assert self.root.is_relative_to(Path(self.temp.name).resolve())
        self.temp.cleanup()

    def manifest_checks(self):
        result = []
        gate.check_manifest(gate.files_in_candidate(), result)
        return result

    def test_selected_package_hashes_match(self):
        self.assertEqual(self.manifest_checks()[0].status, "PASS")

    def test_unlisted_file_blocks_package(self):
        (self.root / "my-notes.md").write_text("personal note", encoding="utf-8")
        self.assertEqual(self.manifest_checks()[0].status, "FAIL")

    def test_modified_file_blocks_package(self):
        with (self.root / "README.md").open("a", encoding="utf-8") as output:
            output.write("\nUnexpected change\n")
        self.assertEqual(self.manifest_checks()[0].status, "FAIL")

    def test_manifest_cannot_reference_parent(self):
        (self.root / "code_manifest.json").write_text(json.dumps({"files": {"../outside.md": "0" * 64}}), encoding="utf-8")
        self.assertEqual(self.manifest_checks()[0].status, "FAIL")

    def test_notebook_attachment_blocks_package(self):
        path = self.root / "Experimento_visual.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        notebook["cells"][0]["attachments"] = {"private.png": {"image/png": "AA=="}}
        path.write_text(json.dumps(notebook), encoding="utf-8")
        checks = []
        gate.check_python_and_json(gate.files_in_candidate(), checks)
        self.assertTrue(any(c.status == "FAIL" and "anexos" in c.name for c in checks))

    def test_notebook_metadata_is_scanned(self):
        path = self.root / "Experimento_visual.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        notebook["metadata"]["origin"] = "C:/" + "Users/" + "private-name/notes"
        path.write_text(json.dumps(notebook), encoding="utf-8")
        checks = []
        gate.check_private_content(gate.files_in_candidate(), checks)
        self.assertEqual(checks[0].status, "FAIL")

    def test_recognizable_token_blocks_package(self):
        (self.root / "unsafe.md").write_text("ghp_" + "a" * 36, encoding="utf-8")
        checks = []
        gate.check_private_content(gate.files_in_candidate(), checks)
        self.assertEqual(checks[0].status, "FAIL")

    def test_malformed_notebook_returns_failure(self):
        (self.root / "Experimento_visual.ipynb").write_text("{", encoding="utf-8")
        checks = []
        gate.check_python_and_json(gate.files_in_candidate(), checks)
        self.assertTrue(any(c.status == "FAIL" and c.name == "JSON e notebook" for c in checks))

    def test_interface_warns_before_local_copies(self):
        page = (self.root / "dist/index.html").read_text(encoding="utf-8")
        video = (self.root / "dist/video.js").read_text(encoding="utf-8")
        self.assertIn("preparar a imagem vai gravar nesta máquina uma cópia", page)
        self.assertIn("upload da pasta pelo navegador vai gravar nesta máquina uma cópia", page)
        self.assertIn("upload vai gravar nesta máquina uma cópia deste vídeo ou GIF", video)
        self.assertGreaterEqual(page.count('class="copy-warning"'), 2)
        self.assertIn('class="copy-warning"', video)

    def test_public_links_and_funding_are_configured(self):
        page = (self.root / "dist/index.html").read_text(encoding="utf-8")
        funding = (self.root / ".github/FUNDING.yml").read_text(encoding="utf-8")
        self.assertIn('href="https://github.com/sponsors/rebojar"', page)
        self.assertIn('href="https://rebojar.github.io/"', page)
        self.assertNotIn('github.com/sponsors/rebojar/button', page)
        self.assertEqual(funding.strip(), "github: rebojar")


if __name__ == "__main__":
    unittest.main(verbosity=2)
