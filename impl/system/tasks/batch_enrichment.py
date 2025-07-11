import asyncio
import json
from src.core.data_access.dgraph_client import DgraphClient
from src.core.data_processing.llm_enrichment import ParallelSemanticEnricher
from src.core.data_access.vectordb_client import VectorDBManager
from src.utils.logger import logger

async def batch_enrichment(batch_size: int = 10):
  dgraph = DgraphClient()
  enricher = ParallelSemanticEnricher()
  vector_db = VectorDBManager()
  
  while True:
    contracts = dgraph.get_contracts(batch_size, enriched=False)
    if not contracts:
      logger.info("No more contracts to enrich")
      break
    
    enriched_contracts = await enricher.process_contracts(contracts)
    dgraph.mutate(enriched_contracts)
    print(enriched_contracts)
    
    if enriched_contracts:
      vector_db.add_embeddings(enriched_contracts)
    
    logger.info(f"Processed {len(enriched_contracts)} contracts")

if __name__ == "__main__":
  asyncio.run(batch_enrichment())