#!/usr/bin/env python3
"""
Script to assign reproducible IDs to existing ContractDeployment records in Dgraph.
This ensures that contracts can be reliably identified even when UIDs change during restore.
"""

import asyncio
import argparse
from typing import Dict
from src.core.data_access.dgraph_client import DgraphClient
from src.utils.logger import logger


async def assign_ids_to_contracts(batch_size: int = 10) -> int:
    """
    Assigns reproducible IDs to all contracts that don't have them.

    Args:
        batch_size: Number of contracts to process in each batch

    Returns:
        Total number of contracts updated
    """
    dgraph = DgraphClient()
    total_updated = 0
    offset = 0

    try:
        # Get total count of contracts
        total_contracts = dgraph.get_contracts_count(enriched=True)
        logger.info(f"Found {total_contracts} total contracts to check for IDs")

        while True:
            # Get batch of contracts
            contracts = dgraph.get_contracts(
                batch_size=batch_size, offset=offset, enriched=True
            )

            if not contracts:
                logger.info("No more contracts to process")
                break

            # Filter contracts that need IDs assigned (empty string or None)
            contracts_needing_ids = []
            for contract in contracts:
                contract_id = contract.get("ContractDeployment.id")
                if not contract_id or contract_id == "":
                    contracts_needing_ids.append(contract)

            if contracts_needing_ids:
                logger.info(
                    f"Processing {len(contracts_needing_ids)} contracts needing IDs in batch {offset // batch_size + 1}"
                )

                # Generate IDs and prepare mutation data
                mutation_batches = []
                for contract in contracts_needing_ids:
                    contract_id = dgraph.generate_contract_id(contract)

                    # Prepare mutation data with UID and new ID
                    mutation_data = {
                        "uid": contract.get("uid"),
                        "ContractDeployment.id": contract_id,
                    }
                    mutation_batches.append(mutation_data)

                    logger.debug(
                        f"Generated ID {contract_id} for contract {contract.get('ContractDeployment.contract', 'unknown')} (UID: {contract.get('uid')})"
                    )

                # Mutate contracts in batches
                if mutation_batches:
                    try:
                        # Process mutations in smaller sub-batches to avoid overwhelming Dgraph
                        sub_batch_size = min(10, len(mutation_batches))
                        for i in range(0, len(mutation_batches), sub_batch_size):
                            sub_batch = mutation_batches[i : i + sub_batch_size]

                            for mutation_data in sub_batch:
                                try:
                                    dgraph.mutate(mutation_data)
                                    total_updated += 1
                                except Exception as e:
                                    logger.error(
                                        f"Failed to mutate contract UID {mutation_data.get('uid')}: {str(e)}"
                                    )
                                    continue

                        logger.info(
                            f"Updated {len(mutation_batches)} contracts with IDs in this batch"
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to update batch at offset {offset}: {str(e)}"
                        )
                        continue
            else:
                logger.debug(
                    f"No contracts needing IDs in batch {offset // batch_size + 1}"
                )

            offset += batch_size

            # Progress update
            if offset % (batch_size * 10) == 0:
                logger.info(
                    f"Progress: processed {offset}/{total_contracts} contracts, updated {total_updated} so far"
                )

        logger.info(
            f"Completed ID assignment. Total contracts updated: {total_updated}"
        )
        return total_updated

    except Exception as e:
        logger.error(f"Error in assign_ids_to_contracts: {str(e)}")
        return total_updated


async def verify_contract_ids() -> Dict[str, int]:
    """
    Verifies that all contracts have IDs assigned.

    Returns:
        Dictionary with counts of contracts with and without IDs
    """
    dgraph = DgraphClient()
    contracts_with_ids = 0
    contracts_without_ids = 0
    offset = 0
    batch_size = 10

    try:
        while True:
            contracts = dgraph.get_contracts(
                batch_size=batch_size, offset=offset, enriched=True
            )

            if not contracts:
                break

            for contract in contracts:
                contract_id = contract.get("ContractDeployment.id")
                if contract_id and contract_id != "":
                    contracts_with_ids += 1
                else:
                    contracts_without_ids += 1
                    logger.warning(
                        f"Contract without ID: {contract.get('ContractDeployment.contract', 'unknown')} (UID: {contract.get('uid', 'unknown')})"
                    )

            offset += batch_size

        logger.info("Verification complete:")
        logger.info(f"  Contracts with IDs: {contracts_with_ids}")
        logger.info(f"  Contracts without IDs: {contracts_without_ids}")
        logger.info(f"  Total contracts: {contracts_with_ids + contracts_without_ids}")

        return {
            "with_ids": contracts_with_ids,
            "without_ids": contracts_without_ids,
            "total": contracts_with_ids + contracts_without_ids,
        }

    except Exception as e:
        logger.error(f"Error in verify_contract_ids: {str(e)}")
        return {"with_ids": 0, "without_ids": 0, "total": 0}


async def test_contract_id_retrieval() -> None:
    """
    Tests retrieving contracts by their reproducible IDs.
    """
    dgraph = DgraphClient()

    try:
        # Get a few contracts with IDs
        contracts = dgraph.get_contracts(batch_size=5, enriched=None)

        for contract in contracts:
            contract_id = contract.get("ContractDeployment.id")
            if contract_id and contract_id != "":
                logger.info(f"Testing retrieval for contract ID: {contract_id}")

                # Try to retrieve by ID
                retrieved_contract = dgraph.get_contract_by_id(contract_id)

                if retrieved_contract:
                    logger.info(
                        f"✓ Successfully retrieved contract by ID {contract_id}"
                    )
                    logger.debug(
                        f"  Contract address: {retrieved_contract.get('ContractDeployment.contract', 'unknown')}"
                    )
                    logger.debug(f"  UID: {retrieved_contract.get('uid', 'unknown')}")
                else:
                    logger.error(f"✗ Failed to retrieve contract by ID {contract_id}")
            else:
                logger.warning(
                    f"Contract without ID: {contract.get('ContractDeployment.contract', 'unknown')} (UID: {contract.get('uid', 'unknown')})"
                )

    except Exception as e:
        logger.error(f"Error in test_contract_id_retrieval: {str(e)}")


async def show_sample_contracts() -> None:
    """
    Shows sample contracts with their IDs for verification.
    """
    dgraph = DgraphClient()

    try:
        contracts = dgraph.get_contracts(batch_size=10, enriched=None)

        logger.info("Sample contracts:")
        for i, contract in enumerate(contracts, 1):
            contract_id = contract.get("ContractDeployment.id", "")
            contract_address = contract.get("ContractDeployment.contract", "unknown")
            uid = contract.get("uid", "unknown")

            status = "✓" if contract_id and contract_id != "" else "✗"
            logger.info(f"{i}. {status} Contract: {contract_address}")
            logger.info(f"   ID: {contract_id or 'EMPTY'}")
            logger.info(f"   UID: {uid}")
            logger.info("   ---")

    except Exception as e:
        logger.error(f"Error in show_sample_contracts: {str(e)}")


async def main():
    """Main function to run the contract ID assignment process."""
    parser = argparse.ArgumentParser(
        description="Assign reproducible IDs to ContractDeployment records"
    )
    parser.add_argument(
        "--batch-size", type=int, default=10, help="Batch size for processing"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing IDs, don't assign new ones",
    )
    parser.add_argument(
        "--test-retrieval", action="store_true", help="Test retrieving contracts by ID"
    )
    parser.add_argument(
        "--show-samples",
        action="store_true",
        help="Show sample contracts with their IDs",
    )
    args = parser.parse_args()

    try:
        if args.verify_only:
            logger.info("Running verification only...")
            stats = await verify_contract_ids()

            if stats["without_ids"] > 0:
                logger.warning(f"Found {stats['without_ids']} contracts without IDs!")
                logger.info(
                    "Run without --verify-only to assign IDs to these contracts"
                )
            else:
                logger.info("✓ All contracts have IDs assigned!")

        elif args.test_retrieval:
            logger.info("Testing contract ID retrieval...")
            await test_contract_id_retrieval()

        elif args.show_samples:
            logger.info("Showing sample contracts...")
            await show_sample_contracts()

        else:
            logger.info("Starting contract ID assignment process...")

            # First verify current state
            logger.info("Verifying current state...")
            stats = await verify_contract_ids()

            if stats["without_ids"] > 0:
                logger.info(
                    f"Found {stats['without_ids']} contracts without IDs. Assigning IDs..."
                )
                updated_count = await assign_ids_to_contracts(
                    batch_size=args.batch_size
                )

                # Verify again after assignment
                logger.info("Verifying after ID assignment...")
                final_stats = await verify_contract_ids()

                if final_stats["without_ids"] == 0:
                    logger.info("✓ All contracts now have IDs assigned!")
                else:
                    logger.warning(
                        f"Still have {final_stats['without_ids']} contracts without IDs"
                    )
            else:
                logger.info("✓ All contracts already have IDs assigned!")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Process failed: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
