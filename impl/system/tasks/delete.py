import asyncio
import argparse
from typing import List, Optional
from src.core.data_access.dgraph_client import DgraphClient
from src.utils.logger import logger


class ArrayFieldDeleter:
    """Handles deletion of array fields from contracts in Dgraph."""

    def __init__(self):
        self.dgraph = DgraphClient()

    def delete_array_fields(
        self,
        contract_ids: Optional[List[str]] = None,
        uids: Optional[List[str]] = None,
        array_fields: Optional[List[str]] = None,
        batch_size: int = 10,
    ) -> int:
        """
        Delete array fields from contracts using UIDs for efficiency.

        Args:
            contract_ids: List of specific contract IDs to delete fields from.
                         If None and uids is None, deletes from all contracts.
            uids: List of specific UIDs to delete fields from.
                 Takes precedence over contract_ids if both are provided.
            array_fields: List of array field names to delete.
                         If None, deletes common array fields.
            batch_size: Number of contracts to process in each batch.

        Returns:
            Number of contracts processed.
        """
        if array_fields is None:
            array_fields = [
                "ContractDeployment.functionalities",
                "ContractDeployment.standards",
                "ContractDeployment.patterns",
            ]

        total_processed = 0

        try:
            if uids:
                # Delete from specific UIDs (most efficient)
                logger.info(f"Deleting array fields from {len(uids)} specific UIDs")
                for uid in uids:
                    self._delete_fields_from_uid(uid, array_fields)
                    total_processed += 1
                    if total_processed % 10 == 0:
                        logger.info(f"Processed {total_processed} contracts")
            elif contract_ids:
                # Delete from specific contract IDs (convert to UIDs first)
                logger.info(
                    f"Deleting array fields from {len(contract_ids)} specific contracts"
                )
                for contract_id in contract_ids:
                    self._delete_fields_from_contract_id(contract_id, array_fields)
                    total_processed += 1
                    if total_processed % 10 == 0:
                        logger.info(f"Processed {total_processed} contracts")
            else:
                # Delete from all contracts in batches
                logger.info("Deleting array fields from all contracts")
                offset = 0

                while True:
                    contracts = self.dgraph.get_contracts(
                        batch_size, offset=offset, enriched=True
                    )
                    if not contracts:
                        break

                    for contract in contracts:
                        uid = contract.get("uid")
                        if uid:
                            self._delete_fields_from_uid(uid, array_fields)
                            total_processed += 1

                    offset += batch_size
                    logger.info(f"Processed {total_processed} contracts so far")

                    if len(contracts) < batch_size:
                        break

            logger.info(
                f"Successfully deleted array fields from {total_processed} contracts"
            )
            return total_processed

        except Exception as e:
            logger.error(f"Error deleting array fields: {str(e)}")
            return total_processed

    def _delete_fields_from_uid(self, uid: str, array_fields: List[str]) -> None:
        """
        Delete specific array fields from a single contract using UID.

        Args:
            uid: The UID of the contract to delete fields from.
            array_fields: List of field names to delete.
        """
        try:
            # Create delete mutation data using UID
            delete_data = {"uid": uid}

            # Add array fields to delete
            for field in array_fields:
                delete_data[field] = None

            # Perform the delete mutation
            with self.dgraph.dgraph_txn() as txn:
                mutation = txn.create_mutation(del_obj=delete_data)
                txn.mutate(mutation=mutation, commit_now=False)

            logger.debug(f"Deleted fields {array_fields} from UID {uid}")

        except Exception as e:
            logger.error(f"Failed to delete fields from UID {uid}: {str(e)}")

    def _delete_fields_from_contract_id(
        self, contract_id: str, array_fields: List[str]
    ) -> None:
        """
        Delete specific array fields from a single contract by contract ID.
        First converts contract ID to UID, then deletes using UID.

        Args:
            contract_id: The contract ID to delete fields from.
            array_fields: List of field names to delete.
        """
        try:
            # Get contract by ID to find UID
            contract = self.dgraph.get_contract_by_id(contract_id)
            if not contract:
                logger.warning(f"Contract {contract_id} not found")
                return

            uid = contract.get("uid")
            if not uid:
                logger.warning(f"No UID found for contract {contract_id}")
                return

            # Delete using UID
            self._delete_fields_from_uid(uid, array_fields)

        except Exception as e:
            logger.error(
                f"Failed to delete fields from contract ID {contract_id}: {str(e)}"
            )

    def list_array_fields(self, contract_id: str = None, uid: str = None) -> None:
        """
        List all array fields for a specific contract.

        Args:
            contract_id: The contract ID to inspect (if uid is not provided).
            uid: The UID to inspect (takes precedence over contract_id).
        """
        try:
            if uid:
                contract = self.dgraph.get_contract_by_uid(uid)
                identifier = f"UID {uid}"
            elif contract_id:
                contract = self.dgraph.get_contract_by_id(contract_id)
                identifier = f"contract {contract_id}"
            else:
                logger.error("Either contract_id or uid must be provided")
                return

            if not contract:
                logger.warning(f"Contract {identifier} not found")
                return

            logger.info(f"Array fields for {identifier}:")

            array_fields = [
                "ContractDeployment.functionalities",
                "ContractDeployment.standards",
                "ContractDeployment.patterns",
            ]

            for field in array_fields:
                value = contract.get(field)
                if value:
                    logger.info(f"  {field}: {value}")
                else:
                    logger.info(f"  {field}: (empty)")

        except Exception as e:
            logger.error(f"Error listing array fields for {identifier}: {str(e)}")


def main():
    """Main function to run the array field deletion script."""
    parser = argparse.ArgumentParser(
        description="Delete array fields from contracts in Dgraph"
    )
    parser.add_argument(
        "--contract-ids", nargs="+", help="Specific contract IDs to delete fields from"
    )
    parser.add_argument(
        "--uids",
        nargs="+",
        help="Specific UIDs to delete fields from (more efficient than contract-ids)",
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        default=[
            "ContractDeployment.functionalities",
            "ContractDeployment.standards",
            "ContractDeployment.patterns",
        ],
        help="Array fields to delete (default: all common array fields)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing contracts (default: 10)",
    )
    parser.add_argument(
        "--list",
        type=str,
        help="List array fields for a specific contract ID instead of deleting",
    )
    parser.add_argument(
        "--list-uid",
        type=str,
        help="List array fields for a specific UID instead of deleting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    try:
        deleter = ArrayFieldDeleter()

        if args.list:
            # List mode with contract ID
            logger.info(f"Listing array fields for contract: {args.list}")
            deleter.list_array_fields(contract_id=args.list)
        elif args.list_uid:
            # List mode with UID
            logger.info(f"Listing array fields for UID: {args.list_uid}")
            deleter.list_array_fields(uid=args.list_uid)
        else:
            # Delete mode
            if args.dry_run:
                logger.info("DRY RUN MODE - No actual deletions will be performed")
                if args.uids:
                    logger.info(
                        f"Would delete fields {args.fields} from UIDs: {args.uids}"
                    )
                elif args.contract_ids:
                    logger.info(
                        f"Would delete fields {args.fields} from contracts: {args.contract_ids}"
                    )
                else:
                    logger.info(
                        f"Would delete fields {args.fields} from all contracts in batches of {args.batch_size}"
                    )
            else:
                # Perform actual deletion
                total_processed = deleter.delete_array_fields(
                    contract_ids=args.contract_ids,
                    uids=args.uids,
                    array_fields=args.fields,
                    batch_size=args.batch_size,
                )
                logger.info(
                    f"Deletion completed. Total contracts processed: {total_processed}"
                )

    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
