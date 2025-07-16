import asyncio
from src.core.data_access.dgraph_client import DgraphClient
from src.core.data_processing.llm_enrichment import ParallelSemanticEnricher
from src.core.data_access.vectordb_client import VectorDBManager
from src.utils.logger import logger

async def batch_enrichment(batch_size: int = 10, update: bool = False):
  dgraph = DgraphClient()
  enricher = ParallelSemanticEnricher()
  vector_db = VectorDBManager(dgraph_client=dgraph)
  
  if update:
    contracts_count = dgraph.get_contracts_count(enriched=True)
    for i in range(0, contracts_count, batch_size):
      contracts = dgraph.get_contracts(batch_size, offset=i, enriched=True)
      enriched_contracts = await enricher.process_contracts(contracts)
      dgraph.mutate(enriched_contracts)
      logger.info(f"Processed {len(enriched_contracts)} contracts")
      print(enriched_contracts)
      
      if enriched_contracts:
        vector_db.add_embeddings(enriched_contracts)
      
      logger.info(f"Processed {len(enriched_contracts)} contracts")
  else:
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
  import argparse

  parser = argparse.ArgumentParser(description="Batch enrichment for contracts")
  parser.add_argument("--update", action="store_true", help="Update already enriched contracts")
  parser.add_argument("--batch-size", type=int, default=10, help="Batch size for enrichment")
  args = parser.parse_args()

  asyncio.run(batch_enrichment(batch_size=args.batch_size, update=args.update))