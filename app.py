import streamlit as st
import tempfile
import os
from pathlib import Path

# --- CONFIGURAÇÕES ---
DEFAULT_MODEL = "phi"
CHUNK_SIZE = 5000
CHUNK_OVERLAP = 400

# --- EXTRAÇÃO DE TEXTO ---
def extract_text(file_path: Path) -> str:
    """Extrai texto usando PyPDF2/python-docx (100% Python puro, sem crash)."""
    ext = file_path.suffix.lower()
    try:
        if ext == ".pdf":
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            return text
        elif ext == ".docx":
            import docx
            doc = docx.Document(str(file_path))
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext == ".txt":
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ""
    except Exception as e:
        raise RuntimeError(f"Erro ao extrair texto: {e}")


# --- FATIAMENTO (CHUNKING) ---
def split_text(text: str) -> list[str]:
    """Divide o texto em fatias usando RecursiveCharacterTextSplitter."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )
    return splitter.split_text(text)

# --- MAP-REDUCE COM LCEL ---
def summarize_map_reduce(chunks: list[str], model_name: str, progress_callback=None) -> str:
    """Executa Map-Reduce usando sintaxe LCEL moderna (pipes)."""
    from langchain_community.chat_models import ChatOllama
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = ChatOllama(model=model_name, temperature=0.0)

    # --- MAP CHAIN (LCEL) ---
    map_prompt = PromptTemplate.from_template(
        "Você é um assistente focado em resumir documentos.\n"
        "Resuma o texto abaixo extraindo os pontos principais de forma concisa:\n\n"
        "\"{text}\"\n\n"
        "RESUMO CONCISO EM PORTUGUÊS:"
    )
    map_chain = map_prompt | llm | StrOutputParser()

    # --- REDUCE CHAIN (LCEL) ---
    reduce_prompt = PromptTemplate.from_template(
        "Aqui está uma coleção de resumos parciais de um documento extenso:\n\n"
        "{text}\n\n"
        "Crie um resumo final coeso e abrangente em PT-BR baseando-se apenas nestas partes.\n"
        "RESUMO FINAL:"
    )
    reduce_chain = reduce_prompt | llm | StrOutputParser()

    # MAP PHASE - Uma fatia por vez (síncrono p/ não estourar 8GB RAM)
    partial_summaries = []
    for i, chunk in enumerate(chunks):
        summary = map_chain.invoke({"text": chunk})
        partial_summaries.append(summary)
        if progress_callback:
            progress_callback(i + 1, len(chunks))

    # REDUCE PHASE - Junta tudo e pede o resumo final
    combined = "\n\n".join(partial_summaries)
    final_summary = reduce_chain.invoke({"text": combined})
    return final_summary

# ================================================================
# INTERFACE STREAMLIT
# ================================================================
st.set_page_config(page_title="Resumidor Local com IA", layout="centered", page_icon="📄")
st.title("📄 Resumidor de Documentos (100% Local)")
st.caption("Sem custos de tokens | Powered by Ollama + LangChain LCEL")

modelo = st.sidebar.text_input("Modelo Ollama:", value=DEFAULT_MODEL)
st.sidebar.markdown("---")
st.sidebar.info(
    "**Como funciona:**\n"
    "1. Extração do texto (unstructured)\n"
    "2. Fatiamento inteligente (LangChain)\n"
    "3. Map-Reduce via Ollama local\n"
    "4. Resumo final unificado"
)

uploaded_file = st.file_uploader("Envie seu arquivo (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    if st.button("🚀 Gerar Resumo"):
        tmp_path = None
        try:
            # Salvar temporariamente
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = Path(tmp.name)

            # 1. EXTRAÇÃO
            with st.spinner("Extraindo texto do documento..."):
                raw_text = extract_text(tmp_path)

            if not raw_text.strip():
                st.warning("Não foi possível extrair texto. O documento pode estar vazio ou ser uma imagem.")
            else:
                st.success(f"✅ Texto extraído! ({len(raw_text)} caracteres)")

                # 2. CHUNKING
                chunks = split_text(raw_text)
                st.info(f"📋 Documento dividido em **{len(chunks)}** partes para caber na memória da IA.")

                # 3. MAP-REDUCE
                progress = st.progress(0, text="Iniciando Map-Reduce...")

                def update_progress(current, total):
                    progress.progress(current / total, text=f"Resumindo parte {current} de {total}... ({modelo})")

                with st.spinner("A IA local está processando. Isso pode levar alguns minutos..."):
                    resultado = summarize_map_reduce(chunks, modelo, progress_callback=update_progress)

                # 4. RESULTADO
                st.subheader("💡 Resumo Final")
                st.write(resultado)
                st.balloons()

        except Exception as e:
            st.error("Ocorreu um erro!")
            st.warning(
                f"Verifique se o Ollama está rodando e se o modelo '{modelo}' foi baixado.\n\n"
                f"Para baixar: `ollama pull {modelo}`"
            )
            st.exception(e)
        finally:
            if tmp_path and tmp_path.exists():
                os.remove(tmp_path)
