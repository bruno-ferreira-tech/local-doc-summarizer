from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

class LLMService:
    @staticmethod
    def summarize_map_reduce(chunks: list[str], model_name: str, progress_callback=None) -> str:
        """Executa Map-Reduce usando sintaxe LCEL moderna sem misturar com logs/tela."""
        llm = ChatOllama(model=model_name, temperature=0.0)

        # --- MAP CHAIN ---
        map_prompt = PromptTemplate.from_template(
            "Você é um assistente focado em resumir documentos.\n"
            "Resuma o texto abaixo extraindo os pontos principais de forma concisa:\n\n"
            "\"{text}\"\n\n"
            "RESUMO CONCISO EM PORTUGUÊS:"
        )
        map_chain = map_prompt | llm | StrOutputParser()

        # --- REDUCE CHAIN ---
        reduce_prompt = PromptTemplate.from_template(
            "Aqui está uma coleção de resumos parciais de um documento extenso:\n\n"
            "{text}\n\n"
            "Crie um resumo final coeso e abrangente em PT-BR baseando-se apenas nestas partes.\n"
            "RESUMO FINAL:"
        )
        reduce_chain = reduce_prompt | llm | StrOutputParser()

        # MAP PHASE
        partial_summaries = []
        for i, chunk in enumerate(chunks):
            summary = map_chain.invoke({"text": chunk})
            partial_summaries.append(summary)
            if progress_callback:
                progress_callback(i + 1, len(chunks))

        # REDUCE PHASE
        combined = "\n\n".join(partial_summaries)
        final_summary = reduce_chain.invoke({"text": combined})
        return final_summary
