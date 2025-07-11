import asyncio
from src.core.data_access.dgraph_client import DgraphClient
from src.core.data_access.vectordb_client import VectorDBManager
from src.utils.logger import logger


async def update_embeddings(batch_size: int = 50):
    """
    Updates embeddings for all enriched smart contracts in the database.

    Args:
        batch_size: Number of contracts to process in each batch
    """
    dgraph = DgraphClient()
    vector_db = VectorDBManager()

    try:
        # Get total count of enriched contracts
        total_contracts = dgraph.get_contracts_count(enriched=True)
        logger.info(f"Found {total_contracts} enriched contracts to add to embeddings")

        if total_contracts == 0:
            logger.info("No enriched contracts found. Nothing to add to embeddings.")
            return

        processed_count = 0
        offset = 0

        # Process contracts in batches
        while processed_count < total_contracts:
            # Get batch of enriched contracts
            contracts = dgraph.get_contracts(
                batch_size=batch_size, offset=offset, enriched=True
            )

            if not contracts:
                logger.info("No more contracts to process")
                break

            # Add contracts to embeddings
            try:
                vector_db.add_embeddings(contracts)
                processed_count += len(contracts)
                offset += batch_size

                logger.info(f"Processed {processed_count}/{total_contracts} contracts")

            except Exception as e:
                logger.error(
                    f"Failed to add embeddings for batch starting at offset {offset}: {str(e)}"
                )
                # Continue with next batch even if current batch fails
                offset += batch_size
                continue

        logger.info(
            f"Successfully processed {processed_count} contracts and added them to embeddings"
        )

    except Exception as e:
        logger.error(f"Error in update_embeddings: {str(e)}")
        raise
    finally:
        dgraph.close()


async def get_contracts_stats():
    """
    Utility function to get statistics about contracts in the database
    """
    dgraph = DgraphClient()

    try:
        total_contracts = dgraph.get_contracts_count(enriched=None)
        enriched_contracts = dgraph.get_contracts_count(enriched=True)
        non_enriched_contracts = dgraph.get_contracts_count(enriched=False)

        logger.info(f"Contract Statistics:")
        logger.info(f"  Total contracts: {total_contracts}")
        logger.info(f"  Enriched contracts: {enriched_contracts}")
        logger.info(f"  Non-enriched contracts: {non_enriched_contracts}")

        return {
            "total": total_contracts,
            "enriched": enriched_contracts,
            "non_enriched": non_enriched_contracts,
        }
    finally:
        dgraph.close()


if __name__ == "__main__":
    # Get contract statistics first
    stats = asyncio.run(get_contracts_stats())

    # Run the update embeddings process
    asyncio.run(update_embeddings())
