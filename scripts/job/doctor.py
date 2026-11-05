"""Diagnóstico local: distingue instalado, observado e pronto, sem criar ``.job``.

Não abre navegador, não lê credenciais e não instala nada. Disponibilidade de
ferramenta nunca comprova sessão autenticada: sessões aparecem só como
observações registradas por ``Workflow.capability()``.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

from scripts.job.workflow import Workflow


def _probe(run, args, timeout=10):
    try:
        done = run(args, capture_output=True, text=True, timeout=timeout, shell=False)
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return done.returncode == 0, (done.stdout or "").strip()[:200]


def doctor(root: Path, *, which=shutil.which, run=subprocess.run) -> dict:
    """Retorna ``{checks: [{id, label, installed, observed, ready, optional, detail}],
    profile, resumes, sessions, ready: {chat, effects}, message}``.

    - installed: executável encontrado; observed: respondeu a ``--version``/``status``;
      ready: utilizável para o controle local.
    - sessions: observações registradas (``usable`` = ready e dentro da validade).
    """
    workflow = Workflow(root)
    checks = []
    python_ok = sys.version_info >= (3, 11)
    checks.append({"id": "python", "label": "Python", "installed": True, "observed": True, "ready": python_ok, "optional": False, "detail": sys.version.split()[0]})
    for tool, optional in (("uv", False),):
        path = which(tool)
        observed, detail = _probe(run, [path, "--version"]) if path else (False, "")
        ready = observed
        checks.append({"id": tool, "label": tool, "installed": bool(path), "observed": observed, "ready": ready, "optional": optional, "detail": detail or "não encontrado"})
    state = workflow.state()
    profile = state["profile"]
    resumes = {"approved_verified": 0, "approved_invalid": 0, "other": 0}
    if state["initialized"]:
        try:
            from scripts.job.resumes import ResumeManager
            manager = ResumeManager(workflow.root)
            for version in manager.list():
                if version["status"] != "approved":
                    resumes["other"] += 1
                    continue
                try:
                    manager.get(version["id"])
                    resumes["approved_verified"] += 1
                except ValueError:
                    resumes["approved_invalid"] += 1
        except (ImportError, ValueError) as exc:
            resumes["error"] = str(exc)[:200]
    sessions = state["capabilities"]
    tools_ok = all(check["ready"] for check in checks if not check["optional"])
    effects = tools_ok and bool(profile.get("approved")) and resumes["approved_verified"] > 0 and any(s["usable"] for s in sessions) and not state["control"]["stopped"]
    ready = {"chat": tools_ok, "effects": effects}
    lines = ["Diagnóstico do Carreira Guiada:"]
    for check in checks:
        level = "pronto" if check["ready"] else "observado" if check["observed"] else "instalado" if check["installed"] else "ausente"
        lines.append(f"- {check['label']}: {level}{' (opcional)' if check['optional'] else ''}")
    lines.append(f"- Perfil: {'aprovado' if profile.get('approved') else 'pendente'}")
    lines.append(f"- Currículos aprovados e íntegros: {resumes['approved_verified']}")
    lines.append(f"- Sessões observadas e válidas: {sum(1 for s in sessions if s['usable'])} (observação não comprova autenticação atual)")
    return {"checks": checks, "profile": profile, "resumes": resumes, "sessions": sessions, "control": state["control"], "ready": ready, "message": "\n".join(lines)}
