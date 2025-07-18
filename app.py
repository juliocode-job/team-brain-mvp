import os
import json
import time
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import chromadb
import chromadb.errors
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- Function to connect to ChromaDB with retries ---
def connect_to_chroma_with_retries(host='chroma', port=8000, retries=5, delay=5):
    """
    Attempts to connect to the ChromaDB server with a retry mechanism.
    """
    for i in range(retries):
        try:
            # Use the service name 'chroma' as the host
            client = chromadb.HttpClient(host=host, port=port)
            client.heartbeat() # Check if the server is responsive
            print("✅ API server successfully connected to ChromaDB.")
            return client
        except Exception as e:
            print(f"⚠️ API connection attempt {i+1}/{retries} failed: {e}")
            if i < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    raise ConnectionError("Could not connect to ChromaDB after several retries.")


# --- 0. Load Access Control List (ACL) ---
with open('acls.json', 'r') as f:
    acls = json.load(f)

# --- 1. Initialize Connections and Models ---
load_dotenv()
print("Initializing connections and models...")
embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(model="gpt-4o")

# Connect to ChromaDB using the new robust function
chroma_client = connect_to_chroma_with_retries(host='chroma')
collection_name = "team_brain_collection"
vector_store = Chroma(
    client=chroma_client,
    collection_name=collection_name,
    embedding_function=embeddings,
)
print("✅ Vector store loaded.")

# --- 2. Define the RAG Chain Template ---
template = """
You are an enterprise assistant. Answer the question based only on the following context.
If you don't know the answer, just say that you don't know.

Context:
{context}

Question:
{question}
"""
prompt = ChatPromptTemplate.from_template(template)

# --- 3. Initialize the Flask API Server ---
app = Flask(__name__)
CORS(app)

# --- 4. Define API Endpoints ---
@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles chat requests from the user, with final robust ACL enforcement.
    """
    data = request.json
    user_id = data.get('user_id')
    user_message = data.get('message')

    if not user_id or not user_message:
        return jsonify({"error": "Please provide both a 'user_id' and a 'message'."}), 400

    # --- ACL ENFORCEMENT ---
    user_permissions = acls.get(user_id, {}).get("permissions", [])

    if not user_permissions:
        return jsonify({"answer": "Access denied. You do not have permissions to any documents."}), 403

    # --- FINAL CORRECTED FILTER LOGIC ---
    search_kwargs = {"k": 2}
    if len(user_permissions) == 1:
        search_kwargs["filter"] = {"source": user_permissions[0]}
    else:
        search_kwargs["filter"] = {"$or": [{"source": doc} for doc in user_permissions]}

    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    # --- DYNAMICALLY CREATE THE CHAIN WITH THE FILTERED RETRIEVER ---
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # --- AUDIT LOG ---
    print(f"INFO: Query from user_id: '{user_id}' | Permissions: {user_permissions} | Message: '{user_message}'")

    bot_response = chain.invoke(user_message)

    return jsonify({"answer": bot_response})


# --- 5. Run the Application ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)