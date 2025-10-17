import streamlit as st
from openai import OpenAI
import time
import os

# Inicialize o cliente OpenAI com sua chave de API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID do assistente existente
assistant_id = "asst_LWlbtAhvA05s3qM0JVfK20M8"  # Substitua pelo ID do assistente pré-criado

# Título do app
st.title("Assistente para análise de processos: ")

# Inicialize o estado da sessão
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Seção para upload de arquivos
st.header("Faça Upload dos Seus Arquivos PDF")
uploaded_files = st.file_uploader("Escolha arquivos PDF para consultar", type="pdf", accept_multiple_files=True)

if uploaded_files and st.button("Processar Arquivos"):
    with st.spinner("Processando arquivos..."):
        # Passo 1: Crie um novo vector store para os arquivos uploadados
        vector_store = client.vector_stores.create(name="User Uploaded PDFs")

        # Passo 2: Prepare e envie os arquivos para o vector store
        file_streams = [file.getvalue() for file in uploaded_files]
        file_batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=[(file.name, stream) for file, stream in zip(uploaded_files, file_streams)]
        )

        # Verifique se o upload foi concluído
        if file_batch.status == "completed":
            st.session_state.vector_store_id = vector_store.id
            st.success(f"Arquivos processados com sucesso! Vector Store ID: {vector_store.id}")

            # Passo 3: Vincule o vector store ao assistente existente
            try:
                client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={
                        "file_search": {
                            "vector_store_ids": [vector_store.id]
                        }
                    }
                )
                st.success("Vector store vinculado ao assistente com sucesso!")
            except Exception as e:
                st.error(f"Erro ao vincular vector store ao assistente: {str(e)}")
        else:
            st.error(f"Erro no processamento: {file_batch.status}")

# Seção para consultas (somente se o vector store estiver pronto)
if st.session_state.vector_store_id:
    st.header("Faça Perguntas sobre os Arquivos")

    # Exiba o histórico de mensagens
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Campo de input para a pergunta
    user_input = st.chat_input("Faça uma pergunta:")

    if user_input:
        # Adicione a mensagem do usuário ao histórico
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Crie uma thread para a consulta
        thread = client.beta.threads.create()

        # Envie a mensagem do usuário
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # Execute o assistente
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id
        )

        # Recupere a resposta
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            for msg in messages:
                if msg.role == "assistant":
                    response = msg.content[0].text.value
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    with st.chat_message("assistant"):
                        st.markdown(response)
                    break
        else:
            st.error(f"Erro: A execução falhou com status: {run.status}")
else:
    if uploaded_files:
        st.info("Clique em 'Processar Arquivos' para começar.")
    else:
        st.info("Faça upload dos arquivos PDF para começar.")

