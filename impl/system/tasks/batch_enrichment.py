import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass

from langchain_huggingface import HuggingFaceEmbeddings
from src.core.data_access.dgraph_client import DgraphClient
from src.core.data_processing.llm_enrichment import ParallelSemanticEnricher
from src.utils.logger import logger


@dataclass
class EnrichmentConfig:
    """Configuration for batch enrichment process."""

    batch_size: int = 10
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    device: str = "cpu"
    normalize_embeddings: bool = True


class BatchEnricher:
    """Handles batch enrichment of smart contracts with semantic analysis and embeddings."""

    def __init__(self, config: EnrichmentConfig):
        self.config = config
        self.dgraph = DgraphClient()
        self.enricher = ParallelSemanticEnricher()
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=config.embedding_model_name,
            model_kwargs={"device": config.device},
            encode_kwargs={"normalize_embeddings": config.normalize_embeddings},
        )

    def _create_contract_text(self, contract: Dict[str, Any]) -> str:
        """Create a text representation of contract for embedding."""
        description = contract.get("ContractDeployment.description", "")
        functionality = contract.get(
            "ContractDeployment.functionality_classification", ""
        )
        domain = contract.get("ContractDeployment.application_domain", "")
        security = contract.get("ContractDeployment.security_risks_description", "")

        return f"description {description} functionality_classification {functionality} application_domain {domain} security_risks_description {security}"

    def _prepare_embedding_data(
        self, contracts: List[Dict[str, Any]]
    ) -> tuple[List[str], List[str], List[Dict[str, str]]]:
        """Prepare data for embedding generation."""
        texts = []
        ids = []
        metadatas = []

        for contract in contracts:
            # Use stable contract ID
            contract_id = contract.get("ContractDeployment.id")
            if contract_id is None or contract_id == "":
                logger.warning(f"Contract missing ID: {contract}")
                continue

            text = self._create_contract_text(contract)
            texts.append(text)
            ids.append(contract_id)
            metadatas.append({"contract_id": contract_id})

        return texts, ids, metadatas

    async def _process_embeddings(self, contracts: List[Dict[str, Any]]) -> None:
        """Process and store embeddings for contracts."""
        if not contracts:
            return

        try:
            texts, ids, metadatas = self._prepare_embedding_data(contracts)

            if not texts:
                logger.warning("No valid texts found for embedding generation")
                return

            embeddings = self.embedding_model.embed_documents(texts)

            # Store embeddings in Dgraph
            for contract, embedding in zip(contracts, embeddings):
                try:
                    contract_id = contract.get("ContractDeployment.id")
                    if contract_id:
                        self.dgraph.insert_embeddings(contract_id, embedding)
                except Exception as e:
                    logger.error(
                        f"Failed to insert embedding for contract ID {contract_id}: {str(e)}"
                    )
                    # Continue with other contracts even if one fails

        except Exception as e:
            logger.error(f"Error processing embeddings: {str(e)}")

    async def _process_batch(self, contracts: List[Dict[str, Any]]) -> int:
        """Process a single batch of contracts."""
        if not contracts:
            return 0

        try:
            # Enrich contracts with semantic analysis
            enriched_contracts = await self.enricher.process_contracts(contracts)

            if enriched_contracts:
                # Update contracts in Dgraph
                self.dgraph.mutate(enriched_contracts)
                logger.info(f"Enriched and stored {len(enriched_contracts)} contracts")

                # Process embeddings
                await self._process_embeddings(enriched_contracts)

                return len(enriched_contracts)
            else:
                logger.warning("No contracts were enriched in this batch")
                return 0

        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            return 0

    async def enrich_new_contracts(self) -> int:
        """Enrich all contracts that haven't been enriched yet."""
        total_processed = 0

        while True:
            try:
                contracts = self.dgraph.get_contracts(
                    self.config.batch_size, enriched=False
                )

                if not contracts:
                    logger.info("No more contracts to enrich")
                    break

                processed_count = await self._process_batch(contracts)
                total_processed += processed_count

                logger.info(f"Total contracts processed: {total_processed}")

            except Exception as e:
                logger.error(f"Error in enrich_new_contracts loop: {str(e)}")
                break

        return total_processed

    async def update_enriched_contracts(self) -> int:
        """Update contracts that have already been enriched."""
        total_processed = 0

        try:
            contracts_count = self.dgraph.get_contracts_count(enriched=True)
            logger.info(f"Found {contracts_count} enriched contracts to update")

            for i in range(0, contracts_count, self.config.batch_size):
                try:
                    contracts = self.dgraph.get_contracts(
                        self.config.batch_size, offset=i, enriched=True
                    )

                    processed_count = await self._process_batch(contracts)
                    total_processed += processed_count

                    logger.info(
                        f"Updated batch {i // self.config.batch_size + 1}, total processed: {total_processed}"
                    )

                except Exception as e:
                    logger.error(f"Error processing batch at offset {i}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error in update_enriched_contracts: {str(e)}")

        return total_processed


async def batch_enrichment(batch_size: int = 10, update: bool = False) -> int:
    """
    Main function to run batch enrichment.

    Args:
        batch_size: Number of contracts to process in each batch
        update: If True, update already enriched contracts; otherwise enrich new contracts

    Returns:
        Total number of contracts processed
    """
    config = EnrichmentConfig(batch_size=batch_size)
    enricher = BatchEnricher(config)

    try:
        if update:
            logger.info("Starting update of enriched contracts...")
            return await enricher.update_enriched_contracts()
        else:
            logger.info("Starting enrichment of new contracts...")
            return await enricher.enrich_new_contracts()

    except Exception as e:
        logger.error(f"Fatal error in batch_enrichment: {str(e)}")
        return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch enrichment for contracts")
    parser.add_argument(
        "--update", action="store_true", help="Update already enriched contracts"
    )
    parser.add_argument(
        "--batch-size", type=int, default=10, help="Batch size for enrichment"
    )
    args = parser.parse_args()

    try:
        total_processed = asyncio.run(
            batch_enrichment(batch_size=args.batch_size, update=args.update)
        )
        logger.info(
            f"Batch enrichment completed. Total contracts processed: {total_processed}"
        )
    except KeyboardInterrupt:
        logger.info("Batch enrichment interrupted by user")
    except Exception as e:
        logger.error(f"Batch enrichment failed: {str(e)}")
        exit(1)
