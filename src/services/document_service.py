from pathlib import Path
import pdfplumber
import docx

class DocumentService:
    CHUNK_SIZE = 5000
    CHUNK_OVERLAP = 400

    @staticmethod
    def extract_text(file_path: Path) -> str:
        """Extrai texto de PDFs, DOCX ou TXT usando lógica 100% livre de PyPDF2."""
        ext = file_path.suffix.lower()
        try:
            if ext == ".pdf":
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                return text
            elif ext == ".docx":
                doc = docx.Document(str(file_path))
                return "\n".join([p.text for p in doc.paragraphs])
            elif ext == ".txt":
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return ""
        except Exception as e:
            raise RuntimeError(f"Erro na camada I/O ao extrair texto do documento: {e}")

    @classmethod
    def split_text(cls, text: str) -> list[str]:
        """Divide o documento extraído em blocos mantendo a coerência semântica."""
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cls.CHUNK_SIZE,
            chunk_overlap=cls.CHUNK_OVERLAP,
            length_function=len
        )
        return splitter.split_text(text)
