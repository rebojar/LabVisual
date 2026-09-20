#!/usr/bin/env python3
"""Verificação estática e reproduzível do candidato a publicação."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

REQUIRED_FILES = {
    ".gitignore",
    "README.md",
    "requirements.txt",
    "config-local.example.json",
    "launcher.py",
    "server.py",
    "dist/index.html",
    "tools/extract_visual.py",
    "INSTALL.md",
    "VALIDATION.md",
    "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "code_manifest.json",
}

FORBIDDEN_DIRS = {
    ".code-backups",
    ".venv",
    "__pycache__",
    "sessions",
    "batches",
    "videos",
    "imports",
    ".runtime",
    ".jupyter",
    ".jupyter-data",
    ".ipynb_checkpoints",
}

FORBIDDEN_SUFFIXES = {
    ".safetensors",
    ".gguf",
    ".pt",
    ".pth",
    ".npz",
    ".npy",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".mp4",
    ".webm",
    ".log",
    ".pid",
}

TEXT_NAMES = {".gitignore", "LICENSE", "NOTICE"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".html", ".js", ".css", ".cmd", ".ipynb"}

MANUAL_CHECKS = [
    "evidências de instalação e execução aplicáveis à revisão final",
    "revisão da seleção e de todos os commits que serão publicados",
    "revisão de segurança dinâmica; o escopo desta edição é uso local",
    "escolha de licença/autoria e obrigações de componentes redistribuídos",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def files_in_candidate() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(ROOT).parts and path.name != '.code-sync.json'
    )


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def add(checks: list[Check], name: str, ok: bool, detail: str) -> None:
    checks.append(Check(name, "PASS" if ok else "FAIL", detail))


def check_inventory(files: list[Path], checks: list[Check]) -> None:
    existing = {relative(path) for path in files}
    missing = sorted(REQUIRED_FILES - existing)
    add(checks, "arquivos obrigatórios", not missing, "completos" if not missing else ", ".join(missing))

    forbidden: list[str] = []
    for path in files:
        rel = path.relative_to(ROOT)
        lowered_parts = {part.lower() for part in rel.parts[:-1]}
        if lowered_parts & FORBIDDEN_DIRS:
            forbidden.append(relative(path))
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or rel.as_posix() == "config-local.json":
            forbidden.append(relative(path))
    forbidden = sorted(set(forbidden))
    add(checks, "ausência de artefatos privados ou pesados", not forbidden, "nenhum" if not forbidden else ", ".join(forbidden))


def check_manifest(files: list[Path], checks: list[Check]) -> None:
    problems = []
    try:
        manifest = json.loads((ROOT / "code_manifest.json").read_text(encoding="utf-8"))
        declared = manifest["files"]
        if not isinstance(declared, dict) or not declared:
            raise ValueError("lista de arquivos vazia ou inválida")
        if len({name.casefold() for name in declared}) != len(declared):
            raise ValueError("nomes ambíguos entre sistemas")
        existing = {relative(path) for path in files}
        extra = sorted(existing - set(declared) - {"code_manifest.json"})
        if extra:
            problems.append("fora da seleção: " + ", ".join(extra))
        for name, expected in declared.items():
            path = ROOT / name
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError("hash inválido no manifesto")
            if Path(name).is_absolute() or ".." in Path(name).parts or "\\" in name:
                raise ValueError("caminho inválido no manifesto")
            if not path.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError("arquivo fora da raiz selecionada")
            if any(parent.is_symlink() or parent.is_junction() for parent in [path, *path.parents] if parent != ROOT and parent.is_relative_to(ROOT)):
                raise ValueError("link ou junção na seleção")
            if not path.is_file():
                problems.append("ausente: " + name)
            elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                problems.append("hash diferente: " + name)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        problems.append(str(exc))
    add(checks, "manifesto e seleção explícita", not problems,
        "arquivos e hashes conferidos" if not problems else " | ".join(problems))


def check_python_and_json(files: list[Path], checks: list[Check]) -> None:
    syntax_errors: list[str] = []
    for path in files:
        if path.suffix.lower() != ".py":
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=relative(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            syntax_errors.append(f"{relative(path)}: {exc}")
    add(checks, "sintaxe Python", not syntax_errors, "válida" if not syntax_errors else " | ".join(syntax_errors))

    json_errors: list[str] = []
    for rel in ("config-local.example.json", "Experimento_visual.ipynb"):
        path = ROOT / rel
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            json_errors.append(f"{rel}: {exc}")
    add(checks, "JSON e notebook", not json_errors, "válidos" if not json_errors else " | ".join(json_errors))

    try:
        notebook = json.loads((ROOT / "Experimento_visual.ipynb").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    saved_outputs = []
    for index, cell in enumerate(notebook.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs") or cell.get("execution_count") is not None:
            saved_outputs.append(str(index))
    add(
        checks,
        "notebook sem execução salva",
        not saved_outputs,
        "nenhuma saída" if not saved_outputs else "células " + ", ".join(saved_outputs),
    )
    attachments = [str(index) for index, cell in enumerate(notebook.get("cells", []), 1) if cell.get("attachments")]
    embedded = "data:image/" in json.dumps(notebook, ensure_ascii=False)
    add(checks, "notebook sem anexos ou imagens embutidas", not attachments and not embedded,
        "nenhum" if not attachments and not embedded else "anexo ou imagem embutida encontrada")


def check_private_content(files: list[Path], checks: list[Check]) -> None:
    patterns = {
        "caminho de perfil Windows": re.compile(r"(?i)[a-z]:[\\/]+users[\\/]+[^\\/\r\n]+"),
        "caminho de perfil Unix": re.compile(r"(?i)(?:^|[\s'\"(])/(?:home|users)/[^/\s'\")]+"),
        "diretório sincronizado pessoal": re.compile("One" + "Drive", re.IGNORECASE),
        "chave privada": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
        "token reconhecível": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b"),
        "URL com token literal": re.compile(r"[?&]token=[A-Za-z0-9_-]{16,}"),
        "segredo literal": re.compile(
            r"(?i)\b(?:api[_-]?key|password|secret)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"
        ),
    }
    findings: list[str] = []
    for path in files:
        if path.resolve() == SELF or (path.name not in TEXT_NAMES and path.suffix.lower() not in TEXT_SUFFIXES):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.append(f"{relative(path)}: não foi possível ler ({exc})")
            continue
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append(f"{relative(path)}: {label}")
    add(checks, "caminhos pessoais e segredos literais", not findings, "nenhum" if not findings else " | ".join(findings))


def check_gitignore(checks: list[Check]) -> None:
    content = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    entries = {line.strip() for line in content if line.strip() and not line.lstrip().startswith("#")}
    required = {
        ".venv/",
        "config-local.json",
        "sessions/",
        "batches/",
        "videos/",
        "imports/",
        "*.safetensors",
        "*.pt",
        "*.npz",
        "*.png",
        "*.mp4",
    }
    missing = sorted(required - entries)
    add(checks, ".gitignore de dados locais", not missing, "cobertura mínima presente" if not missing else ", ".join(missing))


def check_dependencies(checks: list[Check]) -> None:
    lines = [
        line.strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    invalid = [line for line in lines if not re.fullmatch(r"[A-Za-z0-9_.-]+==[^=\s]+", line)]
    names = [line.split("==", 1)[0].lower() for line in lines if "==" in line]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    ok = bool(lines) and not invalid and not duplicates
    detail = f"{len(lines)} dependências fixadas" if ok else f"inválidas={invalid}; duplicadas={duplicates}"
    add(checks, "dependências fixadas", ok, detail)


def check_loopback(checks: list[Check]) -> None:
    service_files = [ROOT / "server.py", ROOT / "picker_service.py", ROOT / "neighbors_service.py"]
    missing_loopback = []
    exposed = []
    for path in service_files:
        text = path.read_text(encoding="utf-8")
        if "127.0.0.1" not in text:
            missing_loopback.append(path.name)
        if "0.0.0.0" in text:
            exposed.append(path.name)
    add(
        checks,
        "serviços restritos ao loopback",
        not missing_loopback and not exposed,
        "127.0.0.1 nos três serviços" if not missing_loopback and not exposed else f"sem loopback={missing_loopback}; expostos={exposed}",
    )


def check_readme(checks: list[Check]) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8").casefold()
    expected = [
        "não houve treinamento",
        "não inclui pesos",
        "instalação validada",
        "validation.md",
        "install.md",
        "127.0.0.1",
        "o pacote de código não inclui resultados experimentais",
    ]
    missing = [phrase for phrase in expected if phrase.casefold() not in readme]
    add(checks, "limites declarados no README", not missing, "presentes" if not missing else ", ".join(missing))


def check_license(checks: list[Check]) -> None:
    path = ROOT / "LICENSE"
    content = path.read_text(encoding="utf-8") if path.is_file() else ""
    # Os textos GNU oficiais incluem exemplos com marcadores no apêndice.
    # Não confundir esses exemplos com a escolha/autoria revisadas à parte.
    ok = len(content.strip()) > 500 and not re.search(r"(?im)^\s*(?:TODO|A DEFINIR|LICENSE PENDING)\s*$", content)
    add(checks, "licença definitiva presente", ok,
        "texto presente; escolha e autoria exigem revisão humana" if ok else "licença ainda não definida ou texto incompleto")


def run() -> list[Check]:
    files = files_in_candidate()
    checks: list[Check] = []
    check_inventory(files, checks)
    check_manifest(files, checks)
    check_python_and_json(files, checks)
    check_private_content(files, checks)
    check_gitignore(checks)
    check_dependencies(checks)
    check_loopback(checks)
    check_readme(checks)
    check_license(checks)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emite o resultado em JSON.")
    args = parser.parse_args()

    checks = run()
    failures = [check for check in checks if check.status == "FAIL"]
    if args.json:
        print(
            json.dumps(
                {
                    "static_gate": "FAIL" if failures else "PASS",
                    "checks": [asdict(check) for check in checks],
                    "outside_static_gate": MANUAL_CHECKS,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for check in checks:
            print(f"[{check.status}] {check.name}: {check.detail}")
        print()
        print("GATE ESTÁTICO:", "FAIL" if failures else "PASS")
        print("Verificações que este comando não comprova:")
        for gate in MANUAL_CHECKS:
            print(f"- {gate}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
