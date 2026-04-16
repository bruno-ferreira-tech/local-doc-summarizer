import streamlit as st
import tempfile
import os
from pathlib import Path

# Injeção das camadas de serviço
from services.document_service import DocumentService
from services.llm_service import LLMService

# --- CONFIGURAÇÕES ---
DEFAULT_MODEL = "phi"

def main():
    st.set_page_config(page_title="Resumidor Local com IA", layout="centered", page_icon="📄")
    st.title("📄 Resumidor de Documentos (100% Local)")
    st.caption("Sem custos de tokens | Powered by Ollama + LangChain LCEL")

    modelo = st.sidebar.text_input("Modelo Ollama:", value=DEFAULT_MODEL)
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**Como funciona:**\n"
        "1. Extração do texto (Camada Service)\n"
        "2. Fatiamento (Chunking)\n"
        "3. Map-Reduce via Ollama\n"
        "4. Resumo unificado"
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
                with st.spinner("Lendo documento via Serviços de I/O..."):
                    raw_text = DocumentService.extract_text(tmp_path)

                if not raw_text.strip():
                    st.warning("Não foi possível extrair texto ou o documento está vazio.")
                    return

                st.success(f"✅ Texto extraído! ({len(raw_text)} caracteres)")

                # 2. CHUNKING
                chunks = DocumentService.split_text(raw_text)
                st.info(f"📋 Documento dividido em **{len(chunks)}** partes para a IA processar de forma segura.")

                # 3. MAP-REDUCE
                progress = st.progress(0, text="Iniciando Map-Reduce...")

                def update_progress(current, total):
                    progress.progress(current / total, text=f"Resumindo parte {current} de {total}... ({modelo})")

                with st.spinner("LLM Service local processando o fluxo (pode levar minutos)..."):
                    resultado = LLMService.summarize_map_reduce(chunks, modelo, progress_callback=update_progress)

                # 4. RESULTADO
                st.subheader("💡 Resumo Final")
                st.write(resultado)
                st.balloons()

            except Exception as e:
                st.error("Ocorreu um erro no processamento!")
                st.warning(f"Certifique-se de que o Ollama está rodando o modelo '{modelo}' localmente.")
                st.exception(e)
            finally:
                if tmp_path and tmp_path.exists():
                    try:
                        os.remove(tmp_path)
                    except:
                        pass

if __name__ == "__main__":
    main()
