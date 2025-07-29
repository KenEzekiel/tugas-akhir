import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_huggingface import HuggingFaceEmbeddings
from src.core.data_access.dgraph_client import DgraphClient
from src.core.data_access.vectordb_client import VectorDBManager
from src.utils.logger import logger


@dataclass
class EmbeddingConfig:
    """Configuration for embedding update process."""

    batch_size: int = 50
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    device: str = "cpu"
    normalize_embeddings: bool = True


class EmbeddingUpdater:
    """Handles updating embeddings for smart contracts in the database."""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.dgraph = DgraphClient()
        self.vector_db = VectorDBManager(dgraph_client=self.dgraph)
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
            # Use stable contract ID instead of UID
            contract_id = contract.get("ContractDeployment.id")
            if contract_id is None or contract_id == "":
                logger.warning(
                    f"Contract missing ID: {contract.get('ContractDeployment.contract', 'unknown')}"
                )
                continue

            text = self._create_contract_text(contract)
            texts.append(text)
            ids.append(contract_id)
            metadatas.append({"contract_id": contract_id})

        return texts, ids, metadatas

    async def _process_embeddings_batch(self, contracts: List[Dict[str, Any]]) -> int:
        """Process and store embeddings for a batch of contracts."""
        if not contracts:
            return 0

        try:
            texts, ids, metadatas = self._prepare_embedding_data(contracts)

            if not texts:
                logger.warning("No valid texts found for embedding generation")
                return 0

            embeddings = self.embedding_model.embed_documents(texts)

            # Store embeddings in Dgraph using UID but also store contract ID for reference
            successful_updates = 0
            for contract, embedding in zip(contracts, embeddings):
                try:
                    uid = contract.get("uid")
                    contract_id = contract.get("ContractDeployment.id")

                    if uid and contract_id:
                        self.dgraph.insert_embeddings(uid, embedding)
                        logger.debug(
                            f"Stored embeddings for contract ID {contract_id} (UID: {uid})"
                        )
                        successful_updates += 1
                    else:
                        logger.warning(
                            f"Missing UID or contract ID for contract: {contract.get('ContractDeployment.contract', 'unknown')}"
                        )

                except Exception as e:
                    contract_id = contract.get("ContractDeployment.id", "unknown")
                    logger.error(
                        f"Failed to insert embedding for contract ID {contract_id}: {str(e)}"
                    )
                    # Continue with other contracts even if one fails

            logger.info(
                f"Successfully updated embeddings for {successful_updates}/{len(contracts)} contracts in batch"
            )
            return successful_updates

        except Exception as e:
            logger.error(f"Error processing embeddings batch: {str(e)}")
            return 0

    async def update_all_embeddings(self) -> int:
        """Update embeddings for all enriched contracts in the database."""
        total_processed = 0
        offset = 0

        try:
            # Get total count of enriched contracts
            total_contracts = self.dgraph.get_contracts_count(enriched=True)
            logger.info(
                f"Found {total_contracts} enriched contracts to update embeddings"
            )

            if total_contracts == 0:
                logger.info("No enriched contracts found. Nothing to update.")
                return 0

            while True:
                try:
                    # Get batch of enriched contracts
                    contracts = self.dgraph.get_contracts(
                        self.config.batch_size, offset=offset, enriched=True
                    )

                    if not contracts:
                        logger.info("No more contracts to process")
                        break

                    # Process embeddings for this batch
                    batch_processed = await self._process_embeddings_batch(contracts)
                    total_processed += batch_processed
                    offset += self.config.batch_size

                    logger.info(
                        f"Progress: {total_processed}/{total_contracts} contracts processed"
                    )

                except Exception as e:
                    logger.error(f"Error processing batch at offset {offset}: {str(e)}")
                    offset += self.config.batch_size
                    continue

            logger.info(
                f"Completed embedding updates. Total contracts processed: {total_processed}"
            )
            return total_processed

        except Exception as e:
            logger.error(f"Error in update_all_embeddings: {str(e)}")
            return total_processed

    async def update_embeddings_for_contracts(self, contract_ids: List[str]) -> int:
        """Update embeddings for specific contracts by their IDs."""
        if not contract_ids:
            logger.warning("No contract IDs provided for embedding update")
            return 0

        total_processed = 0

        try:
            # Process contracts in batches
            for i in range(0, len(contract_ids), self.config.batch_size):
                batch_ids = contract_ids[i : i + self.config.batch_size]

                # Get contracts by IDs
                contracts = []
                for contract_id in batch_ids:
                    try:
                        contract = self.dgraph.get_contract_by_id(contract_id)
                        if contract:
                            contracts.append(contract)
                        else:
                            logger.warning(f"Contract with ID {contract_id} not found")
                    except Exception as e:
                        logger.error(
                            f"Failed to retrieve contract with ID {contract_id}: {str(e)}"
                        )
                        continue

                if contracts:
                    batch_processed = await self._process_embeddings_batch(contracts)
                    total_processed += batch_processed

                logger.info(
                    f"Processed batch {i // self.config.batch_size + 1}, total processed: {total_processed}"
                )

            logger.info(
                f"Completed embedding updates for {total_processed} specified contracts"
            )
            return total_processed

        except Exception as e:
            logger.error(f"Error in update_embeddings_for_contracts: {str(e)}")
            return total_processed

    def close(self) -> None:
        """Close the Dgraph client connection."""
        self.dgraph.close()
        logger.info("Embedding updater closed")


async def update_embeddings(
    batch_size: int = 50, contract_ids: Optional[List[str]] = None
) -> int:
    """
    Main function to update embeddings for smart contracts.

    Args:
        batch_size: Number of contracts to process in each batch
        contract_ids: Optional list of specific contract IDs to update. If None, updates all enriched contracts.

    Returns:
        Total number of contracts processed
    """
    config = EmbeddingConfig(batch_size=batch_size)
    updater = EmbeddingUpdater(config)

    try:
        if contract_ids:
            logger.info(
                f"Starting embedding update for {len(contract_ids)} specific contracts..."
            )
            return await updater.update_embeddings_for_contracts(contract_ids)
        else:
            logger.info("Starting embedding update for all enriched contracts...")
            return await updater.update_all_embeddings()

    except Exception as e:
        logger.error(f"Fatal error in update_embeddings: {str(e)}")
        return 0
    finally:
        updater.close()


async def get_contracts_stats() -> Dict[str, int]:
    """
    Utility function to get statistics about contracts in the database.

    Returns:
        Dictionary with contract statistics
    """
    dgraph = DgraphClient()

    try:
        total_contracts = dgraph.get_contracts_count(enriched=None)
        enriched_contracts = dgraph.get_contracts_count(enriched=True)
        non_enriched_contracts = dgraph.get_contracts_count(enriched=False)

        # Count contracts with embeddings
        contracts_with_embeddings = 0
        offset = 0
        batch_size = 100

        while True:
            contracts = dgraph.get_contracts(
                batch_size=batch_size, offset=offset, enriched=True
            )
            if not contracts:
                break

            for contract in contracts:
                if contract.get("ContractDeployment.embeddings"):
                    contracts_with_embeddings += 1

            offset += batch_size

        stats = {
            "total": total_contracts,
            "enriched": enriched_contracts,
            "non_enriched": non_enriched_contracts,
            "with_embeddings": contracts_with_embeddings,
            "enriched_without_embeddings": enriched_contracts
            - contracts_with_embeddings,
        }

        logger.info("Contract Statistics:")
        logger.info(f"  Total contracts: {stats['total']}")
        logger.info(f"  Enriched contracts: {stats['enriched']}")
        logger.info(f"  Non-enriched contracts: {stats['non_enriched']}")
        logger.info(f"  Contracts with embeddings: {stats['with_embeddings']}")
        logger.info(
            f"  Enriched contracts without embeddings: {stats['enriched_without_embeddings']}"
        )

        return stats

    except Exception as e:
        logger.error(f"Error getting contract statistics: {str(e)}")
        return {
            "total": 0,
            "enriched": 0,
            "non_enriched": 0,
            "with_embeddings": 0,
            "enriched_without_embeddings": 0,
        }
    finally:
        dgraph.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Update embeddings for smart contracts"
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Batch size for processing"
    )
    parser.add_argument(
        "--contract-ids", nargs="+", help="Specific contract IDs to update (optional)"
    )
    parser.add_argument(
        "--stats-only", action="store_true", help="Only show contract statistics"
    )
    args = parser.parse_args()

    try:
        if args.stats_only:
            # Show statistics only
            stats = asyncio.run(get_contracts_stats())
        else:
            # Get statistics first
            stats = asyncio.run(get_contracts_stats())

            # Run the update embeddings process
            total_processed = asyncio.run(
                update_embeddings(
                    batch_size=args.batch_size, contract_ids=args.contract_ids
                )
            )

            logger.info(
                f"Embedding update completed. Total contracts processed: {total_processed}"
            )

    except KeyboardInterrupt:
        logger.info("Embedding update interrupted by user")
    except Exception as e:
        logger.error(f"Embedding update failed: {str(e)}")
        exit(1)
