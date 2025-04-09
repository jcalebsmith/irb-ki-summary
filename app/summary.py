import os
# Remove the old API key retrieval
# api_key = os.getenv("OPENAI_API_KEY")

import concurrent.futures
import json
from pathlib import Path
import re
from sys import argv
from typing import Dict, List, Tuple

# Import Azure specific classes
from llama_index.llms.azure_openai import AzureOpenAI as AzureOpenAILLM
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
# Keep original OpenAI LLM import for type hinting if needed, or remove if unused elsewhere
# from llama_index.llms.openai import OpenAI as OpenAILLM
from llama_index.core.postprocessor import LLMRerank
# Remove original OpenAI Embedding import
# from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.llms import ChatMessage
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import BaseNode, Document
from llama_index.core import Settings, StorageContext, VectorStoreIndex

from .pdf import PDFPages, read_pdf
from .messages_dictionary import messages_dict

# --- Azure OpenAI Configuration ---
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY") # Use Azure key
api_version = os.getenv("OPENAI_API_VERSION")
llm_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_LLM")
embed_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBED")

# Model names can sometimes be specified or inferred from deployment
llm_model_name = "gpt-4o"
embed_model_name = "text-embedding-3-large"

# Initialize Azure embedding model and LLM
embed_model = AzureOpenAIEmbedding(
    model=embed_model_name,
    deployment_name=embed_deployment_name,
    api_key=api_key,
    azure_endpoint=azure_endpoint,
    api_version=api_version,
)

llm = AzureOpenAILLM(
    model=llm_model_name,
    deployment_name=llm_deployment_name,
    api_key=api_key,
    azure_endpoint=azure_endpoint,
    api_version=api_version,
    temperature=0,
    top_p=0.0,
)
# --- End Azure OpenAI Configuration ---


# Set global settings (no change here, just uses the new instances)
Settings.llm = llm
Settings.embed_model = embed_model

class PDFReader(BaseReader):
    def load_data(self, pdf_pages: PDFPages) -> List[Document]:
        pass
        # Iterate over every page
        docs = []

        for (text, label) in zip(pdf_pages.texts, pdf_pages.labels):
            metadata = {"page_label" : label}
            docs.append(Document(text=text, extra_info=metadata))

        return docs


def process_pdf(file_path: Path) -> List[BaseNode]:
    loader = PDFReader()
    documents = loader.load_data(read_pdf(file_path))
    node_parser_instance = HierarchicalNodeParser.from_defaults(chunk_sizes=[512, 256, 128])
    nodes = node_parser_instance.get_nodes_from_documents(documents)
    return get_leaf_nodes(nodes)

def create_storage_context_and_index(nodes: List[BaseNode]) -> Tuple[StorageContext, VectorStoreIndex]:
    storage_context = StorageContext.from_defaults()
    storage_context.docstore.add_documents(nodes)
    vector_store_index = VectorStoreIndex(nodes, storage_context=storage_context)
    return storage_context, vector_store_index

def setup_query_engine(vector_store_index: VectorStoreIndex) -> RetrieverQueryEngine:
    automerging_retriever = vector_store_index.as_retriever(similarity_top_k=8)
    rerank_processor = LLMRerank(top_n=4)
    query_engine = RetrieverQueryEngine.from_args(retriever=automerging_retriever, node_postprocessors=[rerank_processor], verbose=True)
    return query_engine

def process_query(query_engine: RetrieverQueryEngine, query_text: str) -> str:
    response = "{}".format(query_engine.query(query_text))
    return response

def formulate_chat_query(context: str, query_text: str) -> str:
    chat_response = llm.chat(messages=[
        ChatMessage(role="system", content=(
            "## YOUR ROLE\n"
            "You are a bioethicist specializing in patient advocacy and human subjects research. Your focus is on interpreting and explaining Informed Consent documents to potential human subjects research participants.\n\n"
            "## RULES\n"
            "- Ensure all responses are directly grounded in the context you are provided.\n"
            "- Responses should be clear and authoritative, delivered in a more formal tone.\n"
            "- Avoid conjunctive adverbs, discourse markers, and both introductory and conclusive statements.\n"
            "- Do not include disclaimers or refer to yourself as an AI.\n"
            "- Provide information in a way that is clear and understandable to potential research participants.\n"
            "- Prioritize accuracy and relevance in your responses. Do not include unnecessary information."
        )),
        ChatMessage(role="user", content=f"RELEVANT STUDY INFORMATION:\n\n{context}"),
        ChatMessage(role="user", content=query_text)
    ])
    return chat_response.message.content

def cleanup_text(text: str) -> str:
    clean_text = re.sub(r'["`\[\]<>]|---', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def remove_empty_sections(final_responses: Dict[str, str]) -> Dict[str, str]:
    return {k: v for k, v in final_responses.items() if v.strip() not in {"", "' '"}}

def process_section(
    section: str,
    queries: List[str],
    query_engine: RetrieverQueryEngine
) -> Tuple[str, str]:
    context_responses = {}
    final_response = ""

    if len(queries) > 1:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_query, query_engine, query) for query in queries[:-1]]
            for future, query in zip(futures, queries[:-1]):
                try:
                    response = future.result()
                    context_responses[query] = cleanup_text(response)
                except Exception as exc:
                    print(f'Query "{query}" generated an exception: {exc}')

    context = "\n\n".join([f"Q: {query}\nA: {response}" for query, response in context_responses.items()])
    cleaned_context = cleanup_text(context)

    if queries:
        final_query_text = queries[-1]
        final_response = formulate_chat_query(cleaned_context, final_query_text)
        final_response = cleanup_text(final_response)

    return section, final_response

def generate_summary(f) -> str:
    leaf_nodes = process_pdf(f)
    storage_context, vector_store_index = create_storage_context_and_index(leaf_nodes)
    query_engine = setup_query_engine(vector_store_index)

    final_responses = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(messages_dict)) as executor:
        future_to_section = {executor.submit(process_section, section, queries, query_engine): section for section, queries in messages_dict.items()}
        for future in concurrent.futures.as_completed(future_to_section):
            section = future_to_section[future]
            try:
                section, response = future.result()
                final_responses[section] = response
            except Exception as exc:
                print(f'{section} generated an exception: {exc}')

    predefined_entries = {
        "section2": "A research study is different from the regular medical care you receive from your doctor. Research studies hope to make discoveries and learn new information about diseases and how to treat them. You should consider the reasons why you might want to join a research study or why it is not the best decision for you at this time.",
        "section3": "Research studies do not always offer the possibility of treating your disease or condition. Research studies also have different kinds of risks and risk levels, depending on the type of the study. You may also need to think about other requirements for being in the study. For example, some studies require you to travel to scheduled visits at the study site in Ann Arbor or elsewhere. This may require you to arrange travel, change work schedules, find child care, or make other plans. In your decision to participate in this study, consider all of these matters carefully."
    }
    for key, value in predefined_entries.items():
        if key not in final_responses:
            final_responses[key] = value

    final_responses = remove_empty_sections(final_responses)

    final_responses["Total Summary"] = "\n\n".join(final_responses[section] for section in sorted(final_responses))

    return final_responses

if __name__ == "__main__":
    input_filepath = "/Users/rwails/prj/summary/summary-backend/HUM00173014.pdf"
    generate_summary(input_filepath)
