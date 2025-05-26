import asyncio
import json
from src.core.data_access.dgraph_client import DgraphClient
from src.core.data_processing.llm_enrichment import ParallelSemanticEnricher
from src.core.data_access.vectordb_client import VectorDBManager
from src.utils.logger import logger

async def batch_enrichment(batch_size: int = 50):
  dgraph = DgraphClient()
  enricher = ParallelSemanticEnricher()
  vector_db = VectorDBManager()
  
  while True:
    contracts = json.loads(dgraph.get_contracts(batch_size, enriched=False).json)["allContractDeployments"]
    if not contracts:
      logger.info("No more contracts to enrich")
      break
    
    enriched_contracts = await enricher.process_contracts(contracts)
    dgraph.mutate(enriched_contracts, commit_now=True)
    
    if enriched_contracts:
      vector_db.add_embeddings(enriched_contracts)
    
    logger.info(f"Processed {len(enriched_contracts)} contracts")

if __name__ == "__main__":
  asyncio.run(batch_enrichment())