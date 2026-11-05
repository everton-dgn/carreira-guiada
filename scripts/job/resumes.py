"""Local, versioned resumes. Human approval is required before any upload.

Extraction does not confirm facts. A fact links to an imported source ID or a
candidate statement. Drafts record their fact IDs, but this is provenance, not
an automatic proof that all prose is true. The chat must show the full draft to
the candidate before calling approve(). Credentials are never resume facts.
"""

from __future__ import annotations

import hashlib
import json
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
            db.executescript("""
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
            """)
            with db:
                yield db

    def _write(self, relative, data):
        self._check_private()
        path = self.root / relative
        if not path.resolve().is_relative_to(self.private.resolve()):
            raise ValueError("Destino fora da área privada.")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.parent.chmod(0o700)
        with path.open("xb") as handle:
            path.chmod(0o600)
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
        identifier = uuid4().hex
        with self._db(write=True) as db:
            if not source.startswith("candidate:") and not db.execute("SELECT 1 FROM resume_sources WHERE id=?", (source,)).fetchone():
                raise ValueError("Vincule o fato a um currículo importado ou a uma resposta do candidato (candidate:referência).")
            db.execute("INSERT INTO resume_facts VALUES(?,?,?,?,?)", (identifier, text, source, int(confirmed), _now()))
        return {"id": identifier, "text": text, "source": source, "confirmed": confirmed}

    def facts(self):
        self._check_private()
        if not self.db_path.exists():
            return []
        with self._db() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='resume_facts'").fetchone():
                return []
            return [dict(row) for row in db.execute("SELECT * FROM resume_facts ORDER BY created_at,id")]

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
        if version["status"] == "retired":
            raise ValueError("Esta versão foi substituída. Crie uma nova revisão para reativá-la.")
        with self._db(write=True) as db:
            db.execute("UPDATE resume_versions SET status='retired' WHERE label=? AND status='approved' AND id<>?", (version["label"], resume_id))
            db.execute("UPDATE resume_versions SET status='approved', approved_at=? WHERE id=?", (_now(), resume_id))
        return self.get(resume_id)
