import json
from pathlib import Path
from typing import List, Any, Optional
import chromadb
import yaml
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from src.utils.logger import logger

load_dotenv()

class VectorDBManager:
  """
  Manages embedding storage and retrieval from vector databases using LangChain
  Currently supports Chroma
  Reads configurations from a YAML file and initializes the respective client
  """
  
  def __init__(
    self, 
    config_path: str = "config/vectordb.yaml",
    collection_name: Optional[str] = None
    ) -> None:
    
    self.config = self.load_config(config_path)
    
    self.logger = logger.getChild("VectorDBManager")

    # Initialize the embedding model with HuggingFace
    self.embedding_model = HuggingFaceEmbeddings(
      model_name="BAAI/bge-small-en-v1.5",
      model_kwargs={"device": "cpu"},
      encode_kwargs={"normalize_embeddings": True}
    )

    # Use custom collection name if provided, else default to config or "contracts"
    self.collection_name = collection_name or self.config.get("collection_name", "contracts")

    if "chroma" in self.config:
      self.init_chroma(self.config["chroma"])
    else:
      raise ValueError("Config must specify 'chroma' settings.")

  @staticmethod
  def load_config(path: str) -> dict[str, Any]:
    """Loads YAML configuration from the given path"""
    config_file = Path(path)
    if not config_file.exists():
      msg = f"Config file not found: {config_file.absolute()}"
      logger.error(msg)
      raise FileNotFoundError(msg)
    
    try:
      with config_file.open("r") as f:
          config = yaml.safe_load(f)
      if not isinstance(config, dict):
          raise ValueError("Invalid config format. Expected a dictionary.")
      return config
    except yaml.YAMLError as e:
      logger.error(f"Error parsing YAML config: {str(e)}")
      raise
    except Exception as e:
      logger.error(f"Failed to load config file: {str(e)}")
      raise

  def init_chroma(self, config: dict[str, Any]) -> None:
    """Initialize Chroma vector database"""
    persist_directory = config.get("persist_directory")
    if not persist_directory:
      raise ValueError("Missing persist_directory")

    try:
      # Initialize the Chroma client
      self.chroma_client = chromadb.PersistentClient(path=persist_directory)
      # Get or create the collection
      self.chroma_collection = self.chroma_client.get_or_create_collection(
        name=self.collection_name
      )
      
      # Then initialize the LangChain Chroma wrapper as a separate step
      self.vectorstore = Chroma(
        persist_directory=persist_directory,
        collection_name=self.collection_name,
        embedding_function=self.embedding_model
      )
      self.logger.info(f"Chroma initialized successfully with collection: {self.collection_name}")
    except Exception as e:
      self.logger.error(f"Chroma init failed: {str(e)}")
      raise

  def add_embeddings(self, contracts: List[dict[str, Any]]) -> None:
    """
    Generate embeddings for each contract and add to the vector store.
    Each contract is expected to have 'functionality', 'key_features', and 'uid' keys.
    """
    try:
      texts = []
      ids = []
      metadatas = []
      
      for contract in contracts:
        text = f"domain {contract.get('ContractDeployment.domain')} functionality {contract.get('ContractDeployment.functionality', '')} security risks {', '.join(contract.get('ContractDeployment.security_risks', []))}"
        texts.append(text)
        ids.append(contract["uid"])
        # ids.append(contract["ContractDeployment.storage_address"])
        metadatas.append({"dgraph_id": contract["uid"]})
      
      # Get embeddings
      embeddings = self.embedding_model.embed_documents(texts)
      
      # Add directly to chromadb collection
      self.chroma_collection.add(
        embeddings=embeddings,
        documents=texts,
        ids=ids,
        metadatas=metadatas
      )
      self.logger.info(f"Added {len(texts)} embeddings successfully")
    except Exception as e:
      self.logger.error(f"Error when adding embeddings: {str(e)}")
      raise
        
  def get_retriever(self, search_kwargs: dict = None) -> Any:
    """Get a retriever from the vector store"""
    if search_kwargs is None:
      search_kwargs = {"k": 5}
    return self.vectorstore.as_retriever(search_kwargs=search_kwargs)
  
  def search(self, query: str, k: int = 5) -> List[dict[str, Any]]:
    """
    Search for similar documents using the chromadb client directly
    
    Args:
      query: The search query string
      k: Number of results to return
        
    Returns:
      List of dictionaries containing document content and metadata
    """
    try:
      # Get query embedding
      query_embedding = self.embedding_model.embed_query(query)
      
      # Search directly with chromadb
      results = self.chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=k
      )
      
      # Format results
      documents = results.get("documents", [[]])[0]
      metadatas = results.get("metadatas", [[]])[0]
      
      self.logger.info(f"Search completed successfully for query: {query}")
      return [
        {
          "content": doc,
          "metadata": meta
        }
        for doc, meta in zip(documents, metadatas)
      ]
    except Exception as e:
      self.logger.error("Error during search: %s", e)
      raise

if __name__ == "__main__":
  try:
    # Sample contracts for testing
    with open("./data/retrieved_enriched_contracts.json", "r") as file:
      contracts = json.load(file)["allContractDeployments"]
    logger.info("Initializing VectorDBManager...")
    manager = VectorDBManager("config/vectordb.yaml")
    logger.info("VectorDBManager initialized.")

    logger.info("Adding embeddings...")
    manager.add_embeddings(contracts)
    logger.info("Embeddings added successfully.")
    
    # Test search functionality
    print("Testing search functionality...")
    # disini bisa implement searching dengan LLM nya
    # query user -> di augment sama LLM (minta querynya ke deepkseek)
    # augmented query -> baru di vector search
    results = manager.search("Open-source ERC-20 token contract with mint/burn functions and snapshot capabilities.", k=2)
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        print(f"Result {i+1}:")
        print(f"  Content: {result['content']}")
        print(f"  Document ID: {result['metadata']['dgraph_id']}")
      
  except Exception as e:
    logger.error("An error occurred: %s", e)
    print(f"An error occurred: {e}")