import os
import json
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import chromadb
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- 0. Load Access Control List (ACL) ---
with open('acls.json', 'r') as f:
    acls = json.load(f)

# --- 1. Initialize Connections and Models ---
load_dotenv()
print("Initializing connections and models...")
embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(model="gpt-4o")
# New line
chroma_client = chromadb.HttpClient(host='chroma', port=8000)
collection_name = "team_brain_collection"
vector_store = Chroma(
    client=chroma_client,
    collection_name=collection_name,
    embedding_function=embeddings,
)
print("✅ Connections and models initialized.")

# --- 2. Define the RAG Chain Template ---
# We define the template once
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
    # This correctly handles all cases.
    search_kwargs = {"k": 2}
    if len(user_permissions) == 1:
        # If there's only one permission, create a simple "$eq" filter.
        search_kwargs["filter"] = {"source": user_permissions[0]}
    else:
        # If there are multiple, create a valid "$or" filter.
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