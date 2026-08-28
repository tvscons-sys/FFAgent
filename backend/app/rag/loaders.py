"""Load supported source files into LangChain Documents."""

from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document
from openpyxl import load_workbook
from pptx import Presentation

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".xlsx", ".xlsm", ".pptx"}


def load_source_documents(data_dir: Path) -> list[Document]:
	documents: list[Document] = []
	for path in sorted(data_dir.rglob("*")):
		if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
			documents.extend(load_file(path))
	return documents


def load_file(path: Path) -> list[Document]:
	extension = path.suffix.lower()
	if extension == ".pdf":
		documents = PyPDFLoader(str(path)).load()
		return [_add_common_metadata(document, path, "pdf") for document in documents]
	if extension == ".docx":
		documents = Docx2txtLoader(str(path)).load()
		return [_add_common_metadata(document, path, "docx") for document in documents]
	if extension in {".txt", ".md"}:
		documents = TextLoader(str(path), encoding="utf-8").load()
		return [_add_common_metadata(document, path, extension[1:]) for document in documents]
	if extension in {".xlsx", ".xlsm"}:
		return _load_workbook(path)
	if extension == ".pptx":
		return _load_presentation(path)
	raise ValueError(f"Unsupported document extension: {extension}")


def _add_common_metadata(document: Document, path: Path, document_type: str) -> Document:
	document.metadata.update({"source": path.name, "source_path": str(path), "document_type": document_type})
	return document


def _load_workbook(path: Path) -> list[Document]:
	workbook = load_workbook(path, read_only=True, data_only=True)
	documents: list[Document] = []
	for worksheet in workbook.worksheets:
		rows = worksheet.iter_rows(values_only=True)
		headers = [str(value).strip() if value is not None else f"column_{index + 1}" for index, value in enumerate(next(rows, ())) ]
		for row_number, row in enumerate(rows, start=2):
			values = ["" if value is None else str(value).strip() for value in row]
			if not any(values):
				continue
			fields = [f"{header}: {value}" for header, value in zip(headers, values) if value]
			documents.append(Document(
				page_content=" | ".join(fields),
				metadata={
					"source": path.name,
					"source_path": str(path),
					"document_type": "spreadsheet",
					"sheet_name": worksheet.title,
					"row_number": row_number,
					"chunk_strategy": "excel_row",
				},
			))
	workbook.close()
	return documents


def _load_presentation(path: Path) -> list[Document]:
	presentation = Presentation(str(path))
	documents: list[Document] = []
	for slide_number, slide in enumerate(presentation.slides, start=1):
		text_parts: list[str] = []
		for shape in slide.shapes:
			if not shape.has_text_frame:
				continue
			text = shape.text.strip()
			if text:
				text_parts.append(text)
		if text_parts:
			documents.append(Document(
				page_content="\n".join(text_parts),
				metadata={
					"source": path.name,
					"source_path": str(path),
					"document_type": "presentation",
					"slide_number": slide_number,
					"chunk_strategy": "pptx_slide",
				},
			))
	return documents