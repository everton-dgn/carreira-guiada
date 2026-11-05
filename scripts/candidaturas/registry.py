"""Conservative Markdown registry import and a share-safe local report.

This module deliberately does not read profile files, infer job identities from
titles, or turn mail reminders into application confirmations.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REGISTRY_FILES = (
    "historico-candidaturas.md",
    "portais-pendentes.md",
    "vagas-arquivadas.md",
)

_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_STATES = {
    "descoberta", "reservada", "em_preenchimento", "envio_iniciado",
    "resultado_incerto", "bloqueada", "pendente_candidato",
    "pendente_verificacao", "confirmada", "descartada",
}
_STORE_STATES = {
    "confirmada": "confirmed", "descoberta": "discovered",
    "reservada": "blocked", "em_preenchimento": "blocked",
    "envio_iniciado": "pending_verification", "resultado_incerto": "pending_verification",
    "pendente_verificacao": "pending_verification", "pendente_candidato": "candidate_pending",
    "bloqueada": "blocked", "descartada": "discarded",
}
_SECRET_PARAMETER = re.compile(
    r"(?:token|secret|password|passwd|senha|credential|session|cookie|jwt|"
    r"signature|auth|access.?key|api.?key|code|ticket)", re.I,
)
_SAFE_QUERY_KEYS = {"jk", "vjk", "vacancyid", "jobid", "job_id", "id"}
_URL_PATTERN = re.compile(r"https?://[^\s<>\]\[()|`]+", re.I)


def _normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().replace("**", "").replace("`", "").split())


def _clean(value: str) -> str:
    return re.sub(r"<br\s*/?>", "; ", value, flags=re.I).strip().replace("\\|", "|")


def _cells(line: str) -> list[str]:
    parts = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [_clean(part) for part in parts]


class RegistryError(ValueError):
    """Malformed job table: importing part of it would distort the counts."""


def _is_job_header(headers: Sequence[str]) -> bool:
    return "empresa" in headers and ("cargo" in headers or "vaga" in headers)


def _fail(source: str, lineno: int, detail: str):
    # Report position and shape only; a malformed row may hold personal data.
    raise RegistryError(f"{source}: linha {lineno}: {detail}")


def _tables(text: str, source: str = "registro"):
    """Yield (section path, headers, cells), excluding fences and detail prose."""
    sections: dict[int, str] = {}
    lines = text.splitlines()
    index = 0
    fenced = False
    while index < len(lines):
        line = lines[index]
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            index += 1
            continue
        if fenced:
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            level = len(heading.group(1))
            sections = {key: value for key, value in sections.items() if key < level}
            sections[level] = _normalized(heading.group(2))
        if "|" not in line:
            index += 1
            continue
        headers = [_normalized(value) for value in _cells(line)]
        separator = _cells(lines[index + 1]) if index + 1 < len(lines) else []
        if not separator or len(headers) != len(separator) or not all(
            re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in separator
        ):
            if _is_job_header(headers):
                _fail(source, index + 1, "cabeçalho de tabela de vagas sem linha separadora compatível")
            index += 1
            continue
        job_table = _is_job_header(headers)
        index += 2
        while index < len(lines) and "|" in lines[index] and lines[index].strip():
            cells = _cells(lines[index])
            if len(cells) == len(headers):
                yield tuple(sections.values()), headers, cells
            elif job_table:
                _fail(source, index + 1, f"linha de vaga com {len(cells)} células; o cabeçalho define {len(headers)}")
            index += 1


def canonical_public_url(value: str) -> str | None:
    """Keep only HTTPS public references; never persist tokenized links."""
    try:
        parsed = urlsplit(value.rstrip(".,;"))
        host = (parsed.hostname or "").casefold().rstrip(".")
        if parsed.scheme.casefold() != "https" or not host or parsed.username or parsed.password:
            return None
        if parsed.port not in (None, 443):
            return None
        query = parse_qsl(parsed.query, keep_blank_values=True)
        if any(_SECRET_PARAMETER.search(key) for key, _ in query):
            return None
        if parsed.fragment and (
            "=" in parsed.fragment or _SECRET_PARAMETER.search(parsed.fragment)
        ):
            return None
        if re.search(r"/(?:auth|oauth|login|magic|invite|invitation|access|token|reset)(?:/|$)", parsed.path, re.I):
            return None
        safe_query = sorted((key.casefold(), val) for key, val in query if key.casefold() in _SAFE_QUERY_KEYS)
        return urlunsplit(("https", host, parsed.path.rstrip("/") or "/", urlencode(safe_query), ""))
    except (ValueError, UnicodeError):
        return None


def _portal_for_host(host: str) -> str | None:
    for portal, base in (("gupy", "gupy.io"), ("linkedin", "linkedin.com"),
                         ("indeed", "indeed.com"), ("indeed", "indeed.com.br"),
                         ("solides", "vagas.solides.com.br")):
        if host == base or host.endswith("." + base):
            return portal
    return None


def _aliases(text: str) -> list[str]:
    found: set[str] = set()
    # Include the type in the match so application IDs cannot be consumed by
    # the public-job shortcut. An explicit job identity remains authoritative.
    pattern = re.compile(
        r"(?<![\w:])(?:(job|application|app|candidatura):)?"
        r"(gupy|linkedin|indeed|solides|inhire|quickin|orbite|programathor|remotar|"
        r"netvagas|github|lever|teamtailor|abler):([a-zA-Z0-9._~:/-]+)", re.I,
    )
    for match in pattern.finditer(text):
        kind, portal, identifier = match.groups()
        kind = "application" if kind and kind.casefold() in {"application", "app", "candidatura"} else "job"
        if kind == "job" and portal.casefold() in {"gupy", "linkedin", "solides"} and not identifier.isdecimal():
            continue
        found.add(f"{kind}:{portal.casefold()}:{identifier}")
    for raw in _URL_PATTERN.findall(text):
        canonical = canonical_public_url(raw)
        if canonical is None:
            continue
        parsed = urlsplit(canonical)
        portal = _portal_for_host(parsed.hostname or "")
        job_match = None
        if portal in {"gupy", "linkedin"}:
            job_match = re.search(r"/jobs/(?:view/)?(?:[^/]*-)?(\d+)(?:/|$)", parsed.path)
        elif portal == "solides":
            job_match = re.search(r"/(?:vaga|vagas)/(\d+)(?:/|$)", parsed.path)
        if job_match:
            found.add(f"job:{portal}:{job_match.group(1)}")
        elif portal == "indeed":
            identity = dict(parse_qsl(parsed.query)).get("jk") or dict(parse_qsl(parsed.query)).get("vjk")
            if identity:
                found.add(f"job:indeed:{identity}")
        elif portal == "gupy":
            application = re.search(r"/applications?/(\d+)(?:/|$)", parsed.path)
            if application:
                found.add(f"application:gupy:{application.group(1)}")
                continue
        # Homepages, recruiter profiles and sign-in landing pages are evidence,
        # not aliases for every vacancy mentioned alongside them.
        if job_match or re.search(r"/(?:jobs?|vagas?|vacancies|positions|opportunities)(?:/|$)", parsed.path, re.I) or any(
            key in {"jk", "vjk", "vacancyid", "jobid", "job_id"} for key, _ in parse_qsl(parsed.query)
        ):
            found.add("url:" + canonical)
    return sorted(found)


def _date(value: str) -> str | None:
    value = _normalized(value)
    if value in {"", "nao_informado", "nao informado"}:
        return None
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
    written = re.fullmatch(r"(\d{1,2}) de ([a-z]+) de (\d{4})", value)
    local = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", value)
    try:
        if iso:
            return date(*(int(part) for part in iso.groups())).isoformat()
        if written:
            day, month, year = written.groups()
            return date(int(year), _MONTHS[month], int(day)).isoformat()
        if local:
            day, month, year = local.groups()
            return date(int(year), int(month), int(day)).isoformat()
    except (ValueError, KeyError):
        pass
    return None


def _value(row: Mapping[str, str], *keys: str) -> str:
    return next((row[key] for key in keys if row.get(key)), "")


def _safe_evidence(value: str) -> str:
    # Raw registries may contain an old tokenized URL or contact. Neither is
    # needed to establish an event, so avoid propagating them into SQLite/report.
    value = _URL_PATTERN.sub(lambda match: canonical_public_url(match.group()) or "[link privado omitido]", value)
    value = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[contato omitido]", value, flags=re.I)
    value = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[documento omitido]", value)
    value = re.sub(r"(?<!\w)(?:\+?55[ .-]?)?\(?\d{2}\)?[ .-]?\d{4,5}[ .-]\d{4}(?!\d)", "[telefone omitido]", value)
    return value


def _section_state(sections: Sequence[str], row: Mapping[str, str]) -> str:
    confirmed_section = any(section == "candidaturas confirmadas" for section in sections)
    explicit = _normalized(row.get("estado", "")).replace(" ", "_")
    if explicit == "confirmada" and not confirmed_section:
        return "pendente_verificacao"
    if confirmed_section:
        return "confirmada"
    if explicit in _STATES:
        return explicit
    if any("aguardando candidato" in section for section in sections):
        return "pendente_candidato"
    if any("bloqueios de triagem" in section for section in sections):
        return "bloqueada"
    if any("descart" in section for section in sections):
        return "descartada"
    return "pendente_verificacao"


def _caveats(text: str) -> list[str]:
    captured: list[str] = []
    active_level: int | None = None
    for line in text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            if "ressalvas de contagem" in _normalized(heading.group(2)):
                active_level = len(heading.group(1))
            elif active_level is not None and len(heading.group(1)) <= active_level:
                active_level = None
        elif active_level is not None and line.strip():
            captured.append(line.strip())
    return captured


def _read_document(text: str, source: str = "registro") -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    notes: list[str] = []
    for sections, headers, cells in _tables(text, source):
        row = dict(zip(headers, cells))
        if any("lembretes de e-mail" in section for section in sections):
            notes.append("Lembretes de e-mail legados foram excluídos da contagem de vagas; exigem vínculo e classificação de etapa.")
            continue
        if "empresa" not in row or not ("cargo" in row or "vaga" in row):
            continue
        # Detail tables and old unrelated notes are not independent job rows.
        if not any(key in row for key in ("chave", "evidencia", "evidencia preservada", "url", "id publico")):
            continue
        company = _safe_evidence(_value(row, "empresa"))
        title = _safe_evidence(_value(row, "cargo", "vaga"))
        if not company or not title or _normalized(company) == "nao_informado":
            continue
        identity_text = " ".join(_value(row, key) for key in (
            "chave", "aliases", "alias", "url", "id publico", "evidencia", "evidencia preservada",
        ))
        aliases = _aliases(identity_text)
        portal = _safe_evidence(_value(row, "portal")) or next(
            (alias.split(":", 2)[1] for alias in aliases if alias.startswith("job:")), "NAO_INFORMADO",
        )
        state = _section_state(sections, row)
        evidence = _safe_evidence(_value(row, "evidencia preservada", "evidencia")) or None
        # Legacy prose sometimes uses an untyped ID. Keep it in the source;
        # without a namespace it cannot safely establish identity in this ledger.
        if evidence:
            evidence = re.sub(r"\bID\s+\d{8,13}\b", "ID legado não tipado; consultar fonte", evidence)
        record_notes: list[str] = []
        for field, label in (("motivo", "Motivo"), ("proxima acao", "Próxima ação")):
            if row.get(field):
                record_notes.append(f"{label}: {_safe_evidence(row[field])}")
        if state in {"reservada", "em_preenchimento", "envio_iniciado", "resultado_incerto"}:
            record_notes.append(f"Estado original {state}; conferir destino e sessão responsável antes de agir.")
        if state == "confirmada" and not evidence:
            state = "pendente_verificacao"
            record_notes.append("Linha histórica sem evidência de confirmação; confirmação exige conferência.")
        if any(_safe_evidence(cell) != cell for cell in cells):
            record_notes.append("Contatos ou links privados foram omitidos durante a importação.")
        confirmed_at = None
        eligible = None
        if state == "confirmada":
            confirmed_at = _date(_value(row, "data do envio", "data de envio", "data da candidatura", "data de confirmacao"))
            marked_evidence = _normalized(evidence)
            if confirmed_at is None:
                marked_date = re.search(r"\benvio_comprovado=(\d{4}-\d{2}-\d{2})\b", marked_evidence)
                if marked_date:
                    confirmed_at = _date(marked_date.group(1))
            marked_eligibility = re.search(r"\belegibilidade_vigente=(sim|nao)\b", marked_evidence)
            if marked_eligibility:
                eligible = marked_eligibility.group(1) == "sim"
            if confirmed_at is None:
                record_notes.append("Data do envio não comprovada; data de registro não entra na meta do período.")
        public_aliases = [alias for alias in aliases if alias.startswith("job:")]
        identity_verified = bool(public_aliases)
        # Multiple public IDs in the same portal are not silently treated as
        # interchangeable; associations need evidence outside a free-text row.
        by_portal: dict[str, set[str]] = {}
        for alias in public_aliases:
            _, alias_portal, alias_id = alias.split(":", 2)
            by_portal.setdefault(alias_portal, set()).add(alias_id)
        if any(len(identifiers) > 1 for identifiers in by_portal.values()):
            identity_verified = False
            record_notes.append("IDs públicos conflitantes na mesma linha; associação precisa de verificação.")
            # Do not establish aliases joining two potentially different jobs.
            aliases = [alias for alias in aliases if not alias.startswith(("job:", "url:"))]
        if not identity_verified:
            record_notes.append("Identidade pública da oportunidade não verificada; fora da meta até reconciliação.")
        identity_parts = [_normalized(company), _normalized(title), _normalized(portal)]
        identity_parts.extend(aliases)
        source_key = "markdown:" + hashlib.sha256("\x1f".join(identity_parts).encode("utf-8")).hexdigest()
        records.append({
            "source_key": source_key,
            "company": company,
            "title": title,
            "portal": portal,
            "aliases": aliases,
            "state": _STORE_STATES[state],
            "confirmed_at": confirmed_at,
            "evidence": evidence,
            "eligible": eligible,
            "identity_verified": identity_verified,
            "notes": record_notes,
        })
    caveats = _caveats(text)
    for caveat in caveats:
        caveat_aliases = set(_aliases(caveat))
        normalized_caveat = _normalized(caveat)
        for record in records:
            if caveat_aliases.intersection(record["aliases"]) or _normalized(record["company"]) in normalized_caveat:
                record["identity_verified"] = False
                record["notes"].append("Ressalva de contagem no registro exige reconciliação de identidade.")
    if caveats:
        notes.append("Há ressalvas de contagem no registro; as identidades afetadas permanecem pendentes.")
    return records, list(dict.fromkeys(notes))


def read_registry(path: str | Path) -> list[dict]:
    """Read explicitly supplied Markdown; never follow file links in its text."""
    path = Path(path)
    records = _read_document(path.read_text(encoding="utf-8"), path.name)[0]
    for record in records:
        record["source_key"] = path.name + ":" + record["source_key"]
    return records


def read_workspace(root: str | Path) -> tuple[list[dict], list[str]]:
    """Read only the three literal registry filenames, without changing them."""
    root = Path(root)
    records: list[dict] = []
    notes = ["O histórico local é incompleto; os totais cobrem somente os registros importados."]
    documents: list[str] = []
    for filename in REGISTRY_FILES:
        try:
            document = (root / filename).read_text(encoding="utf-8")
            documents.append(document)
            imported, imported_notes = _read_document(document, filename)
            for record in imported:
                record["source_key"] = filename + ":" + record["source_key"]
            records.extend(imported)
            table_rows = sum(1 for _ in _tables(document, filename))
            notes.append(f"{filename}: {len(imported)} linhas de vagas importadas; {table_rows - len(imported)} linhas de tabelas não importadas. Prosa e fichas livres não formam novas vagas.")
            notes.extend(f"{filename}: {note}" for note in imported_notes)
        except (OSError, UnicodeError) as error:
            notes.append(f"{filename}: leitura indisponível ({type(error).__name__}); cobertura incompleta.")
    # A caveat in one file can qualify a historical row in another file.
    for caveat in _caveats("\n\n# Limite entre registros\n\n".join(documents)):
        caveat_aliases = set(_aliases(caveat))
        for record in records:
            if caveat_aliases.intersection(record["aliases"]) or _normalized(record["company"]) in _normalized(caveat):
                record["identity_verified"] = False
                note = "Ressalva de contagem entre registros exige reconciliação de identidade."
                if note not in record["notes"]:
                    record["notes"].append(note)
    return records, list(dict.fromkeys(notes))


def _markdown_cell(value: object) -> str:
    if value is None or value == "":
        return "NAO_INFORMADO"
    return _safe_evidence(str(value)).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_report(summary: Mapping, jobs: Sequence[Mapping], steps: Sequence[Mapping]) -> str:
    """Render already-computed totals and queues, without recalculating counts."""
    labels = {
        "opportunities": "Oportunidades únicas", "unique_opportunities": "Oportunidades únicas",
        "confirmed": "Candidaturas confirmadas", "confirmed_applications": "Candidaturas confirmadas",
        "confirmed_eligible": "Confirmadas compatíveis", "eligible_confirmed": "Confirmadas compatíveis",
        "uncertain": "Envios incertos", "uncertain_applications": "Envios incertos",
        "pending_jobs": "Vagas com ação pendente", "pending_steps": "Etapas pendentes",
        "discarded": "Vagas descartadas", "period_confirmed": "Envios confirmados no período",
        "unverified_identity": "Identidades a verificar", "missing_dates": "Confirmações sem data de envio",
        "identity_unverified": "Identidades a verificar", "confirmed_without_date": "Confirmações sem data de envio",
        "identity_conflicts": "Conflitos de identidade", "unlinked_messages": "Mensagens sem vínculo",
        "messages": "Mensagens registradas", "since": "Início do período", "until": "Fim do período",
        "scope": "Alcance da consulta",
        "record_count": "Registros importados, incluindo identidades pendentes",
        "historical_confirmed_records": "Linhas históricas confirmadas, antes da reconciliação",
        "active_record_count": "Registros na importação atual",
        "inactive_records": "Versões antigas preservadas fora da contagem",
        "compatible_unknown": "Confirmações com compatibilidade a verificar",
    }
    lines = ["# Acompanhamento de candidaturas", "", "Totais dos registros locais, com contagem por identidade única.", "", "| Indicador | Total |", "| --- | --- |"]
    for key, value in summary.items():
        if key in {"notes", "warnings", "ressalvas"} or not isinstance(value, (str, int, float, bool)):
            continue
        lines.append(f"| {_markdown_cell(labels.get(key, key))} | {_markdown_cell(value)} |")
    lines.extend(["", "## Vagas", "", "| Empresa | Cargo | Estado | Chave |", "| --- | --- | --- | --- |"])
    for job in jobs:
        key = job.get("opportunity_key", job.get("id", job.get("source_key")))
        lines.append("| " + " | ".join(_markdown_cell(value) for value in (
            job.get("company"), job.get("title"), job.get("state"), key,
        )) + " |")
    if not jobs:
        lines.append("| Nenhuma vaga importada | NAO_INFORMADO | NAO_INFORMADO | NAO_INFORMADO |")
    lines.extend(["", "## Etapas complementares", "", "| Empresa ou processo | Etapa | Estado | Prazo | Próxima ação |", "| --- | --- | --- | --- | --- |"])
    for step in steps:
        lines.append("| " + " | ".join(_markdown_cell(value) for value in (
            step.get("company", step.get("opportunity_key", step.get("opportunity_id"))),
            # The step's own summary or type; the job title is not the step.
            step.get("summary") or step.get("kind") or step.get("action_type") or step.get("step_key"),
            step.get("state"), step.get("due_at", step.get("deadline")),
            step.get("next_action") or step.get("reason"),
        )) + " |")
    if not steps:
        lines.append("| Nenhuma etapa registrada | NAO_INFORMADO | NAO_INFORMADO | NAO_INFORMADO | NAO_INFORMADO |")
    notes: list[str] = []
    for key in ("notes", "warnings", "ressalvas"):
        value = summary.get(key, [])
        notes.extend([value] if isinstance(value, str) else value if isinstance(value, Sequence) else [])
    if notes:
        lines.extend(["", "## Alcance e ressalvas", ""])
        lines.extend(f"- {_markdown_cell(note)}" for note in dict.fromkeys(notes))
    return "\n".join(lines) + "\n"
