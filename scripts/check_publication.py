"""Check the exact Git index without printing private values. No network or writes."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess

ROOT_FILES = {"README.md", "AGENTS.md", "CLAUDE.md", "LICENSE", "NOTICE", "SECURITY.md",
              "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "CHANGELOG.md", ".gitignore",
              ".gitattributes", "pyproject.toml", "uv.lock", "job"}
PUBLIC_DIRS = {"scripts", "tests", "templates", "docs", ".github", ".githooks", ".agents", ".claude"}
PRIVATE_PARTS = {".job", ".git", ".venv", "__pycache__", ".polyhive", "backups", "backup", "node_modules", ".ssh", ".aws", ".kube"}
PRIVATE_NAMES = {"credentials.json", "secrets.json", "id_rsa", "id_ed25519", ".npmrc", ".netrc", "settings.local.json"}
PRIVATE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".crt", ".pdf", ".docx", ".doc", ".sqlite", ".sqlite3", ".db", ".zip", ".gz", ".tar", ".log", ".bak", ".pyc"}
EMAIL = re.compile(r"[A-Za-z0-9_.+%-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
AUTH_URL = re.compile(r"https?://[^\s/'\"<>]+:[^\s/'\"<>]+@([A-Za-z0-9.:-]+)")
RESERVED_DOMAINS = {"example.com", "example.net", "example.org"}
# Exact, visually reviewed originals. Retain their generated C2PA provenance.
REVIEWED_IMAGES = {
    "docs/assets/meu-plano-ilustrado.png": "f9fcf1e6547192e2209701c510b17d6664909bc7e9e755c1a88cbc0420100a69",
    "docs/assets/minha-evolucao-ilustrada.png": "7df7c05c5dd34d2751dfe70954160a40b1f1246f0b1e60d02fd6274a83495c39",
    "docs/assets/plano-carreira-banner.png": "0577d5ee271a8e92b5a40a7e30e73c519253b23f919f182ebb8be66d81ba4d2d",
    "docs/assets/propostas-comparacao-banner.png": "1bdce581389023f22447c4a60ad7b8b835f473da2afebd817f3d8cd439a11ba2",
    "docs/assets/pesquisa-empresa-banner.png": "73d09b61a09b1df1006a544ae14fcc4dfa42e4c0cc25c5ce5f0f2dd1300dfdae",
    "docs/assets/perfil-projetos-banner.png": "e146a5434afd7aa997309401e006b0962316e2a9a6af91eb53fb7fa2587977c4",
    "docs/assets/carreira-guiada-automacao-banner.png": "18a0242b83791649429bd6c178f5a513f1e21952ac1714c50546e457b97c0e77",
    "docs/assets/jornada-candidaturas-banner.png": "c00e1f7258c07cca5a19eb671ed76475b4f3e81e28b088a27e2597ed3806b9da",
    "docs/assets/retornos-progresso-banner.png": "c83526b7ebb4fb548d6b50f4ece547b3501302b0da0dbaf3e9d597c6a0a340d5",
    "docs/assets/benchmark-modelos-banner.png": "b4e360cfb5755a81e80feac4a8e640c142b55bfca17ff4c362a434d7d630336f",
}
PATTERNS = {
    "caminho de usuário do computador": re.compile(r"(?:/(?:Users|home)/[^\s/'\"<>]+|[A-Za-z]:[\\/]Users[\\/][^\s\\/]+|/(?:private/)?var/folders/[^\s]+)"),
    "chave privada": re.compile(r"-----BEGIN (?:(?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----"),
    "token de acesso": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{32,}|[sr]k_live_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|npm_[A-Za-z0-9]{30,}|(?:AKIA|ASIA)[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{16,})\b"),
}


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def path_problem(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        return "caminho inválido"
    if any(part in PRIVATE_PARTS for part in path.parts):
        return "diretório privado ou gerado"
    if (path.name in PRIVATE_NAMES or path.name.startswith((".env", "service_account"))
            or path.suffix.lower() in PRIVATE_SUFFIXES):
        return "arquivo privado, anexo ou credencial"
    if len(path.parts) == 1 and name not in ROOT_FILES:
        return "arquivo da raiz não previsto para publicação"
    if len(path.parts) > 1 and path.parts[0] not in PUBLIC_DIRS:
        return "diretório não previsto para publicação"
    return None


def image_problem(name, data):
    if not name.startswith("docs/assets/"):
        return "imagem fora da pasta de documentação"
    if name in REVIEWED_IMAGES and hashlib.sha256(data).hexdigest() == REVIEWED_IMAGES[name]:
        return None
    if name.endswith(".png"):
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "PNG inválido"
        offset = 8
        while offset + 12 <= len(data):
            size = struct.unpack(">I", data[offset:offset + 4])[0]
            kind = data[offset + 4:offset + 8]
            if offset + size + 12 > len(data):
                return "PNG truncado"
            if kind not in {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS"}:
                return "metadados de imagem exigem conferência explícita"
            offset += size + 12
            if kind == b"IEND":
                return None if offset == len(data) else "dados adicionais após a imagem"
        return "PNG incompleto"
    if name.endswith(".gif"):
        if not data.startswith((b"GIF87a", b"GIF89a")) or len(data) < 13:
            return "GIF inválido"
        offset = 13 + (3 * 2 ** ((data[10] & 7) + 1) if data[10] & 128 else 0)
        try:
            while offset < len(data):
                marker = data[offset]
                offset += 1
                if marker == 0x3B:
                    return None if offset == len(data) else "dados adicionais após a animação"
                if marker == 0x21:
                    label = data[offset]
                    offset += 1
                    if label not in {0xF9, 0xFF}:
                        return "comentário ou extensão não necessária na animação"
                    if label == 0xFF:
                        if (data[offset:offset + 14] != b"\x0bNETSCAPE2.0\x03\x01"
                                or data[offset + 16] != 0):
                            return "metadados de aplicação não previstos"
                        offset += 17
                        continue
                    if data[offset] != 4 or data[offset + 5] != 0:
                        return "bloco de controle GIF inválido"
                    offset += 6
                    continue
                elif marker == 0x2C:
                    packed = data[offset + 8]
                    offset += 9 + (3 * 2 ** ((packed & 7) + 1) if packed & 128 else 0) + 1
                else:
                    return "bloco GIF inválido"
                while data[offset]:
                    offset += data[offset] + 1
                offset += 1
        except IndexError:
            return "GIF truncado"
        return "GIF incompleto"
    return "tipo de imagem não previsto"


def content_problems(name, data):
    if len(data) > 10 * 1024 * 1024:
        return ["arquivo acima de 10 MB"]
    if name.endswith((".png", ".gif")):
        problem = image_problem(name, data)
        return [problem] if problem else []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["arquivo binário não previsto"]
    if "\x00" in text:
        return ["conteúdo binário não previsto"]
    problems = [label for label, pattern in PATTERNS.items() if pattern.search(text)]
    for match in EMAIL.finditer(text):
        domain = match.group(1).lower()
        if domain not in RESERVED_DOMAINS and not domain.endswith((".example", ".invalid", ".test")):
            problems.append("e-mail fora dos domínios fictícios permitidos")
            break
    for match in AUTH_URL.finditer(text):
        domain = match.group(1).split(':')[0].lower()
        if domain not in RESERVED_DOMAINS and not domain.endswith((".example", ".invalid", ".test")):
            problems.append("URL com credencial fora de exemplo fictício")
            break
    return problems


def check(root):
    findings = []
    entries = git(root, "ls-files", "--stage", "-z").split(b"\0")
    checked = 0
    for entry in filter(None, entries):
        header, raw_name = entry.split(b"\t", 1)
        mode, blob, stage = header.decode("ascii").split()
        name = raw_name.decode("utf-8", errors="replace")
        problem = path_problem(name)
        if stage != "0" or mode not in {"100644", "100755"}:
            problem = "conflito, link simbólico ou submódulo não permitido"
        if problem:
            findings.append((name, problem))
            continue  # Never read the content of credential/private paths.
        data = git(root, "cat-file", "blob", blob)
        findings.extend((name, problem) for problem in content_problems(name, data))
        checked += 1
    if not entries or not any(entries):
        findings.append(("índice Git", "nenhum arquivo preparado para publicação"))
    return checked, findings


def main():
    parser = argparse.ArgumentParser(description="Confere os arquivos exatos preparados no Git, sem mostrar valores privados.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--staged", action="store_true", help="Conferir o índice Git (comportamento padrão)")
    args = parser.parse_args()
    try:
        checked, findings = check(args.root)
    except (OSError, subprocess.CalledProcessError, ValueError):
        print("Não consegui conferir o índice Git. Verifique o repositório antes de publicar.")
        return 1
    for index, (name, reason) in enumerate(findings, 1):
        # Paths can themselves contain personal data; report only position and category.
        print(f"Item {index}: {reason}")
    print(f"{checked} arquivo(s) conferido(s); {len(findings)} impedimento(s).")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
