from system.src.core.data_access.vectordb import VectorDBManager
from utils.file import write_file
from utils.logger import logger
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

class LightweightRetriever:
  def __init__(self):
    """
    Initialize the LightweightRetriever with necessary components
    """
    
    self.logger = logger.getChild("LightweightRetriever")
    try:
      self.vector_store = VectorDBManager("config/vectordb.yaml")
      self.llm = init_chat_model("gpt-3.5-turbo", model_provider="openai")
    except Exception as e:
      self.logger.error(f"Failed to initialize retriever: {e}")
      raise
  
  def search(self, query: str, k: int = 5) -> dict:
    """
    Perform a search in the vector store
    """
    
    self.logger.info(f"Preprocessing query {query}")
    preprocessed_query = self.preprocess_query(query)
    self.logger.info(f"Preprocessed query: {preprocessed_query}")
    results = self.vector_store.search(preprocessed_query, k=k)
    self.logger.info(f"Found {len(results)} results:")
    for i, result in enumerate(results):
      print(f"Result {i+1}:")
      print(f"  Content: {result['content']}")
      print(f"  Document ID: {result['metadata']['dgraph_id']}")
    # Postprocessing deleted
    return results
  
  def preprocess_query(self, query: str) -> str:
    """
    Preprocess the query string
    """
    
    query_expansion_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a smart contract search assistant. Expand or rephrase user queries with relevant technical terms, standards, and concepts without changing the original intent. Follow these rules:

    1. Identify key components: Token types (ERC-20/ERC-721), functions (mint/burn), standards (ERC-1155), security terms
    2. Append common synonyms and technical equivalents
    3. Keep additions concise and comma-separated
    4. Never explain - only output the expanded query
    
    Common Smart Contract Concepts to Reference:
    - Standards: ERC-20, ERC-721, ERC-1155, ERC-2981, EIP-712
    - Security: reentrancy guard, overflow checks, access control
    - Patterns: proxy contracts, upgradeability, factory pattern

    Example: 
    User: "NFT contract with royalties"
    Output: "NFT contract with royalties, ERC-2981 standard, royalty payments, ERC-721/ERC-1155, royalty distribution"""),
    
    ("human", "User query: {user_query}")
    ])
    
    chain = query_expansion_prompt | self.llm
    response = chain.invoke({"user_query": query}).content
    self.logger.debug(f"Expanded query: {response}")
    return response
    
if __name__ == "__main__":
  retriever = LightweightRetriever()
  query = """
  Find DAO governance contracts deployed after 2023-06-01 that: 
  - Implement token-based voting 
  - Have upgrade mechanisms 
  - Interact with at least 2 DeFi protocols 
  - With audit-confirmed security properties
  """
  results = retriever.search(query)
  print("Search results:", results)

  write_file(results, 'retrieved_results.json')