import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import chromadb
import chromadb.errors

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
            print("✅ Ingest script successfully connected to ChromaDB.")
            return client
        except Exception as e:
            print(f"⚠️ Ingest connection attempt {i+1}/{retries} failed: {e}")
            if i < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    raise ConnectionError("Could not connect to ChromaDB after several retries.")


# Load environment variables from .env file
load_dotenv()

# --- 1. Load Documents ---
print("Loading documents...")
loader = DirectoryLoader('data/', glob="**/*.md", show_progress=True)
documents = loader.load()
print(f"Loaded {len(documents)} documents.")


# --- 2. Clean Document Metadata ---
print("Cleaning up metadata...")
for doc in documents:
    doc.metadata['source'] = os.path.basename(os.path.dirname(doc.metadata['source']))


# --- 3. Split Documents into Chunks ---
print("Splitting documents into chunks...")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(documents)
print(f"Split documents into {len(chunks)} chunks.")

# --- 4. Initialize Embeddings and Vector Store ---
print("Initializing embeddings model...")
embeddings = OpenAIEmbeddings()
print("Initializing ChromaDB client...")
# Connect using the new robust function
chroma_client = connect_to_chroma_with_retries(host='chroma')
collection_name = "team_brain_collection"

# --- 5. Create Vector Store and Add Chunks ---
print("Creating vector store and adding documents...")
try:
    chroma_client.delete_collection(name=collection_name)
    print("Deleted old collection.")
except chromadb.errors.NotFoundError:
    print("Collection not found, creating a new one.")
    pass

vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    client=chroma_client,
    collection_name=collection_name
)

print("\n✅ Ingestion complete.")
print(f"Total chunks stored in ChromaDB: {vector_store._collection.count()}")
