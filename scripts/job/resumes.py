"""Local, versioned resumes. Human approval is required before any upload.

Extraction does not confirm facts. A fact links to an imported source ID or a
candidate statement. Drafts record their fact IDs, but this is provenance, not
an automatic proof that all prose is true. The chat must show the full draft to
the candidate before calling approve(). Credentials are never resume facts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape
from zipfile import ZipFile

MAX_BYTES = 15 * 1024 * 1024
_SECRET = re.compile(r"(?i)\b(?:password|senha|token|cookie|secret|api[_ -]?key|cpf|rg)\s*[:=]\s*\S+")
_IMPORT_DOCUMENT = re.compile(r"(?i)\b(?:cpf|rg|cnh|passaporte|passport)\b\s*(?:n[º°o.]*\s*)?[:=]?\s*\d|\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_IMPORT_BLOCKED = (
    "O arquivo não foi importado porque parece conter documento de identidade, senha ou código de acesso. "
    "Nada dele foi copiado e suas respostas anteriores continuam salvas. O arquivo original fica onde está. "
    "Faça uma cópia, apague dela CPF, RG e outros documentos, senhas e códigos, e anexe a cópia limpa aqui no chat "
    "ou cole o texto sem esses dados."
)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value, name, limit=100_000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Informe {name} como texto, com até {limit} caracteres.")
    if _SECRET.search(value):
        raise ValueError("Não inclua senhas, códigos de acesso ou documentos de identidade.")
    return value.strip()


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _plain_inline(text):
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    return re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__|`([^`]+)`", lambda m: next(g for g in m.groups() if g is not None), text)


def _blocks(markdown):
    paragraph = []
    for line in markdown.splitlines() + [""]:
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        bullet = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if not line.strip() or heading or bullet:
            if paragraph:
                yield "paragraph", 0, _plain_inline(" ".join(paragraph))
                paragraph = []
            if heading:
                yield "heading", len(heading[1]), _plain_inline(heading[2])
            elif bullet:
                yield "bullet", 0, _plain_inline(bullet[1])
        else:
            paragraph.append(line.strip())


def _extraction_preserved(expected, actual, allow_line_wraps=False):
    """Allow PDF word wrapping only across a line break, preserving word order."""
    wanted = re.findall(r'\w+', expected.casefold())
    actual = actual.casefold()
    tokens = list(re.finditer(r'\w+', actual))
    index = 0
    for word in wanted:
        if index == len(tokens):
            return False
        token = tokens[index].group()
        while allow_line_wraps and token != word and word.startswith(token) and index + 1 < len(tokens):
            gap = actual[tokens[index].end():tokens[index + 1].start()]
            if not re.fullmatch(r'[ \t]*\r?\n[ \t]*', gap):
                break
            index += 1
            token += tokens[index].group()
        if token != word:
            return False
        index += 1
    return bool(wanted) and index == len(tokens)


def _render(markdown):
    """Generate a restrained, searchable PDF and editable DOCX from one source."""
    import reportlab
    from docx import Document
    from docx.shared import Cm, Pt
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    font_dir = Path(reportlab.__file__).parent / "fonts"
    for name, filename in (("JobSans", "Vera.ttf"), ("JobSansBold", "VeraBd.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    styles = {
        "body": ParagraphStyle("body", fontName="JobSans", fontSize=10, leading=14, spaceAfter=5, textColor=colors.HexColor("#222222")),
        "h1": ParagraphStyle("h1", fontName="JobSansBold", fontSize=18, leading=23, spaceAfter=10),
        "h2": ParagraphStyle("h2", fontName="JobSansBold", fontSize=12, leading=17, spaceBefore=11, spaceAfter=5, keepWithNext=True),
        "h3": ParagraphStyle("h3", fontName="JobSansBold", fontSize=10.5, leading=15, spaceBefore=7, spaceAfter=4, keepWithNext=True),
        "bullet": ParagraphStyle("bullet", fontName="JobSans", fontSize=10, leading=14, leftIndent=11, firstLineIndent=-8, spaceAfter=4),
    }
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(1.7)
    section.left_margin = section.right_margin = Cm(1.8)
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Arial", Pt(10)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.15
    for level, size in ((1, 18), (2, 12), (3, 10.5)):
        style = document.styles[f"Heading {level}"]
        style.font.name, style.font.size, style.font.bold = "Arial", Pt(size), True
        style.paragraph_format.keep_with_next = True
    story = []
    for kind, level, text in _blocks(markdown):
        font_name = "JobSansBold" if kind == "heading" else "JobSans"
        supported = pdfmetrics.getFont(font_name).face.charWidths
        missing = {ch for ch in text if not ch.isspace() and ord(ch) not in supported}
        if missing:
            raise ValueError("O texto contém caracteres que a fonte de exportação não suporta. Revise a versão antes de gerar o PDF.")
        if kind == "heading":
            style_key = "h1" if level == 1 else "h2" if level == 2 else "h3"
            document.add_heading(text, level=min(level, 3))
            story.append(Paragraph(escape(text), styles[style_key]))
        elif kind == "bullet":
            document.add_paragraph(text, style="List Bullet")
            story.append(Paragraph("&#8226; " + escape(text), styles["bullet"]))
        else:
            document.add_paragraph(text)
            story.append(Paragraph(escape(text), styles["body"]))
    if not story:
        raise ValueError("O currículo precisa ter conteúdo antes da exportação.")
    pdf, docx = BytesIO(), BytesIO()
    SimpleDocTemplate(pdf, pagesize=A4, topMargin=48, bottomMargin=48, leftMargin=51, rightMargin=51, title="Currículo", author="").build(story)
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.core_properties.title = "Currículo"
    document.save(docx)
    return pdf.getvalue(), docx.getvalue()


class ResumeManager:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.private = self.root / ".job"
        self.db_path = self.private / "control.sqlite3"

    def _check_private(self):
        for path in (self.private, self.db_path, self.private / "resumes", self.private / "sources"):
            if path.is_symlink():
                raise ValueError("A área privada não pode usar links simbólicos.")

    @contextmanager
    def _db(self, write=False):
        from .profile import Profile
        self._check_private()
        with Profile(self.root)._db(write=write) as db:
            if db is None:
                yield None
                return
            db.row_factory = sqlite3.Row
            if not write:
                yield db
                return
            schema = """
          CREATE TABLE IF NOT EXISTS resume_sources (
            id TEXT PRIMARY KEY, label TEXT NOT NULL, original_path TEXT NOT NULL,
            sha256 TEXT NOT NULL, text_path TEXT NOT NULL, created_at TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS resume_facts (
            id TEXT PRIMARY KEY, text TEXT NOT NULL, source TEXT NOT NULL,
            confirmed INTEGER NOT NULL, created_at TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS resume_versions (
            id TEXT PRIMARY KEY, label TEXT NOT NULL, paths TEXT NOT NULL,
            sha256 TEXT NOT NULL, hashes TEXT NOT NULL, fact_ids TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL, approved_at TEXT
          );
          CREATE TABLE IF NOT EXISTS resume_fact_revocations (
            fact_id TEXT PRIMARY KEY, kind TEXT NOT NULL, replaced_by TEXT,
            source TEXT NOT NULL, reason TEXT, retired_versions TEXT NOT NULL,
            created_at TEXT NOT NULL
          );
            """
            # executescript would commit Profile's BEGIN IMMEDIATE before the
            # fact checks. Keep that lock through validation and mutation.
            for statement in schema.split(';'):
                if statement.strip():
                    db.execute(statement)
            with db:
                yield db

    def _write(self, relative, data):
        self._check_private()
        path = self.root / relative
        if not path.resolve().is_relative_to(self.private.resolve()):
            raise ValueError("Destino fora da área privada.")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.parent.chmod(0o700)
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as handle:
            handle.write(data)
        return relative

    def _read(self, relative):
        self._check_private()
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError("Referência inválida ao arquivo de currículo.")
        path = self.root / relative
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != self.root and p.is_relative_to(self.root)):
            raise ValueError("O currículo não pode apontar para um link simbólico.")
        if not path.resolve().is_relative_to(self.private.resolve()) or not path.is_file():
            raise ValueError("Arquivo de currículo ausente ou fora da área privada.")
        return path.read_bytes()

    def import_file(self, path, label):
        label = _text(label, "o nome da versão", 100)
        path = Path(path)
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in {".pdf", ".docx", ".md", ".txt"}:
            raise ValueError("Selecione um arquivo PDF, DOCX, Markdown ou texto, sem link simbólico.")
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("O arquivo excede 15 MB. Envie uma versão menor do currículo.")
        data = path.read_bytes()
        suffix = path.suffix.lower()
        try:
            if suffix == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(data))
                if reader.is_encrypted or len(reader.pages) > 50:
                    raise ValueError("Use um PDF sem senha e com até 50 páginas.")
                extracted = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            elif suffix == ".docx":
                from docx import Document
                from docx.oxml.ns import qn
                with ZipFile(BytesIO(data)) as archive:
                    if sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024:
                        raise ValueError("O DOCX contém dados demais para a importação segura.")
                document = Document(BytesIO(data))
                extracted = "\n".join("".join(node.text or "" for node in p.iter(qn("w:t"))) for p in document.element.body.iter(qn("w:p")))
            else:
                extracted = data.decode("utf-8-sig")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Não consegui ler esse arquivo. Envie outra cópia ou cole o texto no chat.") from exc
        if isinstance(extracted, str) and (_SECRET.search(extracted) or _IMPORT_DOCUMENT.search(extracted)):
            # Checked before any write: the blocked file is never copied to .job.
            raise ValueError(_IMPORT_BLOCKED)
        extracted = _text(extracted, "o texto extraído do currículo")
        identifier = uuid4().hex
        with self._db(write=True) as db:
            original = self._write(f".job/sources/{identifier}/original{suffix}", data)
            text_path = self._write(f".job/sources/{identifier}/texto.txt", extracted.encode())
            db.execute("INSERT INTO resume_sources VALUES(?,?,?,?,?,?)", (identifier, label, original, _hash(data), text_path, _now()))
        return {"id": identifier, "label": label, "original_path": original, "sha256": _hash(data), "text_path": text_path, "text": extracted, "confirmed": False}

    def add_fact(self, text, source, confirmed):
        text, source = _text(text, "o fato", 5000), _text(source, "a origem", 300)
        if type(confirmed) is not bool:
            raise ValueError("A confirmação precisa ser sim ou não, sem valor presumido.")
        with self._db(write=True) as db:
            return self._insert_fact(db, text, source, confirmed)

    @staticmethod
    def _insert_fact(db, text, source, confirmed):
        if not source.startswith("candidate:") and not db.execute("SELECT 1 FROM resume_sources WHERE id=?", (source,)).fetchone():
            raise ValueError("Vincule o fato a um currículo importado ou a uma resposta do candidato (candidate:referência).")
        identifier = uuid4().hex
        db.execute("INSERT INTO resume_facts VALUES(?,?,?,?,?)", (identifier, text, source, int(confirmed), _now()))
        return {"id": identifier, "text": text, "source": source, "confirmed": confirmed}

    def facts(self):
        """All facts, including history. status: active, revoked or replaced (replaced_by)."""
        self._check_private()
        if not self.db_path.exists():
            return []
        with self._db() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_facts'").fetchone():
                return []
            rows = [dict(row) for row in db.execute("SELECT * FROM resume_facts ORDER BY created_at,id")]
            changes = {}
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_fact_revocations'").fetchone():
                changes = {row["fact_id"]: row for row in db.execute("SELECT * FROM resume_fact_revocations")}
        for row in rows:
            change = changes.get(row["id"])
            row["status"] = change["kind"] if change else "active"
            row["replaced_by"] = change["replaced_by"] if change else None
        return rows

    @staticmethod
    def _revocation(db, fact_id):
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_fact_revocations'").fetchone():
            return None
        return db.execute("SELECT * FROM resume_fact_revocations WHERE fact_id=?", (fact_id,)).fetchone()

    def _change_inputs(self, fact_id, source, reason, confirmed):
        if not isinstance(fact_id, str) or not re.fullmatch(r"[0-9a-f]{32}", fact_id):
            raise ValueError("Informe o identificador do fato a corrigir, como aparece na lista de fatos.")
        source = _text(source, "a origem", 300)
        if type(confirmed) is not bool or confirmed is not True:
            raise ValueError("Corrigir ou retirar um fato exige a confirmação explícita da pessoa (confirmed: true).")
        reason = None if reason is None else _text(reason, "o motivo", 1000)
        return source, reason

    def _invalidate(self, db, fact_id, kind, replaced_by, source, reason):
        """Retire every dependent version, of any label, and keep intake consistent.

        Runs inside the caller's write transaction. Resume files are not rewritten and
        workflow authorizations are only reported: an open one may already have an effect.
        """
        retired = []
        for resume_id, fact_ids, status in db.execute("SELECT id, fact_ids, status FROM resume_versions").fetchall():
            if fact_id in json.loads(fact_ids) and status != "retired":
                retired.append(resume_id)
                db.execute("UPDATE resume_versions SET status='retired' WHERE id=?", (resume_id,))
        db.execute("INSERT INTO resume_fact_revocations VALUES(?,?,?,?,?,?,?)",
                   (fact_id, kind, replaced_by, source, reason, json.dumps(retired), _now()))
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='job_intake'").fetchone():
            row = db.execute("SELECT value FROM job_intake WHERE id=1").fetchone()
            state = json.loads(row[0]) if row else None
            if state:
                answers = state.get("answers", {})
                linked = [field for field, answer in answers.items() if answer and answer.get("fact_id") == fact_id]
                for field in linked:
                    if replaced_by:
                        text = db.execute("SELECT text FROM resume_facts WHERE id=?", (replaced_by,)).fetchone()[0]
                        answers[field] = {"text": text, "fact_id": replaced_by}
                    else:
                        del answers[field]
                if linked:
                    db.execute("UPDATE job_intake SET value=? WHERE id=1", (json.dumps(state, ensure_ascii=False),))
        return retired

    def _open_authorizations(self, db, fact_id):
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='wf_actions'").fetchone():
            return []
        versions = [resume_id for resume_id, fact_ids in db.execute("SELECT id, fact_ids FROM resume_versions") if fact_id in json.loads(fact_ids)]
        if not versions:
            return []
        marks = ",".join("?" * len(versions))
        rows = db.execute(f"SELECT id, action, status, resume_id FROM wf_actions WHERE status IN ('authorized','uncertain') AND resume_id IN ({marks}) ORDER BY id", versions)
        return [dict(row) for row in rows]

    def _fact_state(self, db, fact_id):
        fact = dict(db.execute("SELECT * FROM resume_facts WHERE id=?", (fact_id,)).fetchone())
        change = self._revocation(db, fact_id)
        fact.update(status=change["kind"] if change else "active", replaced_by=change["replaced_by"] if change else None)
        return fact

    def _current_fact(self, db, fact_id):
        """Follow replacements to the fact in force; None when the chain ends revoked."""
        while True:
            change = self._revocation(db, fact_id)
            if not change:
                return fact_id
            if not change["replaced_by"]:
                return None
            fact_id = change["replaced_by"]

    def _change_result(self, db, fact_id, duplicate):
        change = self._revocation(db, fact_id)
        replacement = self._fact_state(db, change["replaced_by"]) if change["replaced_by"] else None
        return {"fact": self._fact_state(db, fact_id), "replacement": replacement, "current_fact_id": self._current_fact(db, fact_id),
                "kind": change["kind"], "source": change["source"],
                "reason": change["reason"], "retired_versions": json.loads(change["retired_versions"]),
                "open_authorizations": self._open_authorizations(db, fact_id), "duplicate": duplicate}

    def _superseded(self, db, fact_id):
        current = self._current_fact(db, fact_id)
        if current is None:
            return "Este fato já foi substituído e a versão mais recente foi retirada. Registre um fato novo se a pessoa quiser incluí-lo."
        return "Este fato já foi substituído. Corrija ou retire o fato atual: " + current + "."

    def revoke_fact(self, fact_id, source, confirmed, reason=None):
        """Withdraw a fact. Kept as history; dependent versions become retired."""
        source, reason = self._change_inputs(fact_id, source, reason, confirmed)
        if not source.startswith("candidate:"):
            raise ValueError("A retirada de um fato precisa vir de uma resposta da pessoa (candidate:referência).")
        with self._db(write=True) as db:
            if not db.execute("SELECT 1 FROM resume_facts WHERE id=?", (fact_id,)).fetchone():
                raise ValueError("Fato não encontrado.")
            change = self._revocation(db, fact_id)
            if change and change["kind"] == "revoked":
                return self._change_result(db, fact_id, True)
            if change:
                raise ValueError(self._superseded(db, fact_id))
            self._invalidate(db, fact_id, "revoked", None, source, reason)
            return self._change_result(db, fact_id, False)

    def replace_fact(self, fact_id, text, source, confirmed, reason=None):
        """Correct a fact with a new confirmed one, keeping the old one as history."""
        source, reason = self._change_inputs(fact_id, source, reason, confirmed)
        text = _text(text, "o fato corrigido", 5000)
        with self._db(write=True) as db:
            row = db.execute("SELECT text FROM resume_facts WHERE id=?", (fact_id,)).fetchone()
            if not row:
                raise ValueError("Fato não encontrado.")
            change = self._revocation(db, fact_id)
            if change and change["kind"] == "replaced":
                current = db.execute("SELECT text, source FROM resume_facts WHERE id=?", (change["replaced_by"],)).fetchone()
                if (current["text"], current["source"]) == (text, source):
                    return self._change_result(db, fact_id, True)
                raise ValueError(self._superseded(db, fact_id))
            if change:
                raise ValueError("Este fato foi retirado. Registre um fato novo se a pessoa quiser incluí-lo de novo.")
            if row["text"] == text:
                raise ValueError("O texto corrigido é igual ao atual. Informe a correção confirmada pela pessoa.")
            replacement = self._insert_fact(db, text, source, True)
            self._invalidate(db, fact_id, "replaced", replacement["id"], source, reason)
            return self._change_result(db, fact_id, False)

    def sources(self):
        self._check_private()
        if not self.db_path.exists():
            return []
        with self._db() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_sources'").fetchone():
                return []
            return [dict(row) for row in db.execute("SELECT * FROM resume_sources ORDER BY created_at,id")]

    def draft(self, label, markdown, fact_ids):
        label, markdown = _text(label, "o nome da versão", 100), _text(markdown, "o currículo")
        if not isinstance(fact_ids, list) or not fact_ids or any(not isinstance(value, str) for value in fact_ids) or len(set(fact_ids)) != len(fact_ids):
            raise ValueError("Informe os identificadores únicos dos fatos confirmados usados nesta versão.")
        identifier = uuid4().hex
        with self._db(write=True) as db:
            for fact in fact_ids:
                row = db.execute("SELECT confirmed FROM resume_facts WHERE id=?", (fact,)).fetchone()
                if not row or not row[0]:
                    raise ValueError("A versão usa um fato ausente ou ainda não confirmado pelo candidato.")
                if self._revocation(db, fact):
                    raise ValueError("A versão usa um fato retirado ou substituído. Use o fato atual da lista de fatos.")
            pdf, docx = _render(markdown)
            contents = {"md": (markdown + "\n").encode(), "pdf": pdf, "docx": docx}
            paths = {fmt: self._write(f".job/resumes/{identifier}/curriculo.{fmt}", content) for fmt, content in contents.items()}
            hashes = {fmt: _hash(content) for fmt, content in contents.items()}
            db.execute("INSERT INTO resume_versions VALUES(?,?,?,?,?,?,?,?,?)", (identifier, label, json.dumps(paths), hashes["pdf"], json.dumps(hashes), json.dumps(fact_ids), "draft", _now(), None))
        return self.get(identifier)

    def _version(self, row):
        result = dict(row)
        for key in ("paths", "hashes", "fact_ids"):
            result[key] = json.loads(result[key])
        return result

    def get(self, resume_id):
        _text(resume_id, "o identificador", 64)
        if not self.db_path.exists():
            raise ValueError("Ainda não existe uma versão do currículo.")
        with self._db() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_versions'").fetchone():
                raise ValueError("Ainda não existe uma versão do currículo.")
            row = db.execute("SELECT * FROM resume_versions WHERE id=?", (resume_id,)).fetchone()
            if not row:
                raise ValueError("Versão do currículo não encontrada.")
            result = self._version(row)
        for fmt, path in result["paths"].items():
            if _hash(self._read(path)) != result["hashes"][fmt]:
                raise ValueError("O arquivo foi alterado depois da revisão. Gere e aprove uma nova versão.")
        return result

    def list(self):
        self._check_private()
        if not self.db_path.exists():
            return []
        with self._db() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_versions'").fetchone():
                return []
            rows = db.execute("SELECT * FROM resume_versions ORDER BY created_at,id").fetchall()
        return [self._version(row) for row in rows]

    def approve(self, resume_id):
        version = self.get(resume_id)
        with self._db(write=True) as db:
            row = db.execute("SELECT status, fact_ids FROM resume_versions WHERE id=?", (resume_id,)).fetchone()
            if any(self._revocation(db, fact) for fact in json.loads(row["fact_ids"])):
                raise ValueError("Esta versão usa um fato retirado ou substituído. Gere uma nova versão com os fatos atuais.")
            if row["status"] == "retired":
                raise ValueError("Esta versão foi substituída. Crie uma nova revisão para reativá-la.")
            db.execute("UPDATE resume_versions SET status='retired' WHERE label=? AND status='approved' AND id<>?", (version["label"], resume_id))
            db.execute("UPDATE resume_versions SET status='approved', approved_at=? WHERE id=?", (_now(), resume_id))
        return self.get(resume_id)

    def check(self, resume_id):
        """Check extraction fidelity locally; this is not an ATS ranking score."""
        from docx import Document
        from pypdf import PdfReader
        version = self.get(resume_id)
        markdown = self._read(version['paths']['md']).decode('utf-8')
        blocks = list(_blocks(markdown))
        expected = ' '.join(text for _, _, text in blocks)
        pdf = PdfReader(BytesIO(self._read(version['paths']['pdf'])))
        document = Document(BytesIO(self._read(version['paths']['docx'])))
        texts = {'pdf': '\n'.join(page.extract_text() or '' for page in pdf.pages),
                 'docx': '\n'.join(paragraph.text for paragraph in document.paragraphs)}
        checks = {fmt + '_text_preserved': _extraction_preserved(expected, text, allow_line_wraps=fmt == 'pdf')
                  for fmt, text in texts.items()}
        checks['clear_sections'] = any(kind == 'heading' and level == 2 for kind, level, _ in blocks)
        checks['no_docx_tables'] = not document.tables
        checks['no_markdown_tables'] = not any(re.match(r'^\s*\|.*\|\s*$', line) for line in markdown.splitlines())
        issues = [name for name, passed in checks.items() if not passed]
        explanations = {'pdf_text_preserved': 'O texto extraído do PDF difere do rascunho.',
                        'docx_text_preserved': 'O texto extraído do Word difere do rascunho.',
                        'clear_sections': 'Separe as seções com títulos de nível 2 (## no rascunho).',
                        'no_docx_tables': 'Troque as tabelas do Word por parágrafos.',
                        'no_markdown_tables': 'Troque as tabelas do rascunho por parágrafos.'}
        message = 'Conferência local de leitura aprovada.' if not issues else 'A conferência local encontrou pontos para corrigir:\n' + '\n'.join('- ' + explanations[name] for name in issues)
        message += '\nA IA ainda deve revisar os fatos, os termos da vaga e a prévia no portal; isto não garante classificação em ATS.'
        return {'resume_id': resume_id, 'checks': checks, 'passed': not issues,
                'pages': len(pdf.pages), 'issues': issues, 'ats_score': None, 'message': message}
