import os
import json
import pydgraph
from src.utils.logger import logger
from src.utils.file import write_file
from contextlib import contextmanager
from langchain_huggingface import HuggingFaceEmbeddings


class DgraphClient:
    """
    Interface for interacting with Dgraph database
    """

    def __init__(self, host: str = "localhost", port: int = 9081) -> None:
        self.logger = logger.getChild("DgraphClient")
        self.client_stub = pydgraph.DgraphClientStub(f"{host}:{port}")
        self.client = pydgraph.DgraphClient(self.client_stub)

        # Initialize embedding model for vector search
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    @contextmanager
    def dgraph_txn(self, read_only: bool = False):
        """
        Creates a transaction for Dgraph operations

        Args:
          read_only: Whether the transaction is read-only

        Returns:
          A Dgraph transaction object
        """
        txn = self.client.txn(read_only=read_only)
        try:
            yield txn
            if not read_only:
                txn.commit()
        except Exception as e:
            raise
        finally:
            txn.discard()

    def alter_schema(self, schema: str) -> None:
        """
        Alters the database schema.

        Args:
          schema: A string containing the new schema
        """
        try:
            op = pydgraph.Operation(schema=schema)
            self.client.alter(op)
            self.logger.info("Schema altered successfully")
        except Exception as e:
            self.logger.exception(f"Failed to alter schema: {str(e)}")
            raise

    def get_contracts(
        self, batch_size: int = 5, offset: int = 0, enriched: bool = False
    ) -> dict[str, str]:
        """
        Retrieves unenriched contracts without a semantic description

        Args:
          batch_size: Maximum number of results to return

        Returns:
          The Dgraph query response
        """
        query = f"""
    {{
      allContractDeployments(func: type(ContractDeployment), first:{batch_size}, offset: {offset}) 
      @filter(eq(ContractDeployment.verified_source, true) AND 
      {"" if enriched else "NOT"} has(ContractDeployment.description)) 
      {{
        uid
        ContractDeployment.contract
        ContractDeployment.block
        ContractDeployment.storage_protocol
        ContractDeployment.storage_address
        ContractDeployment.experimental
        ContractDeployment.solc_version
        ContractDeployment.verified_source
        ContractDeployment.verified_source_code
        ContractDeployment.name
        ContractDeployment.description
        ContractDeployment.description_embedding
        ContractDeployment.functionality_classification
        ContractDeployment.application_domain
        ContractDeployment.security_risks_description
      }}
    }}
    """
        with self.dgraph_txn(read_only=True) as txn:
            try:
                response = txn.query(query).json
                response = json.loads(response)["allContractDeployments"]
                self.logger.info(
                    f"Retrieved {'' if enriched else 'un'}enriched contracts ({len(response)})"
                )
                return response
            except Exception as e:
                self.logger.exception("Dgraph query failed")
                raise

    def get_contract_by_uid(self, uid: str) -> dict:
        """
        Retrieves a contract by its UID.

        Args:
          uid: The UID of the contract to retrieve.

        Returns:
          The Dgraph query response as a dict.
        """
        query = f"""
    {{
      contract(func: uid("{uid}")) {{
      uid
      ContractDeployment.contract
      ContractDeployment.block
      ContractDeployment.storage_protocol
      ContractDeployment.storage_address
      ContractDeployment.experimental
      ContractDeployment.solc_version
      ContractDeployment.verified_source
      ContractDeployment.verified_source_code
      ContractDeployment.name
      ContractDeployment.description
      ContractDeployment.functionality_classification
      ContractDeployment.application_domain
      ContractDeployment.security_risks_description
      }}
    }}
    """
        with self.dgraph_txn(read_only=True) as txn:
            try:
                response = txn.query(query).json
                response = json.loads(response)["contract"]
                self.logger.info(f"Retrieved contract with UID {uid}")
                return response
            except Exception as e:
                self.logger.exception(
                    f"Failed to retrieve contract with UID {uid}: {e}"
                )
                raise

    def mutate(self, mutation_data: dict[str, str]) -> dict:
        """
        Performs a mutation (insert/update) in the database

        Args:
          mutation_data: A dictionary to be converted to JSON for the mutation.

        Returns:
          The mutation response
        """
        with self.dgraph_txn() as txn:
            try:
                mutation = txn.create_mutation(set_obj=mutation_data)
                response = txn.mutate(mutation=mutation, commit_now=False)
                self.logger.info("Mutation successful")
                return response
            except Exception as e:
                self.logger.exception("Mutation failed")
                raise

    def insert_embeddings(self, uid: str, embeddings: list[float]) -> None:
        """
        Inserts embeddings for a contract into Dgraph

        Args:
            uid: The UID of the contract to update
            embeddings: List of embedding values to store
        """
        try:
            # Ensure embeddings are float32 values
            embeddings_float32 = [float(e) for e in embeddings]

            # Format embeddings as quoted JSON string for float32vector
            embeddings_str = json.dumps(embeddings_float32)

            mutation_data = {
                "uid": uid,
                "ContractDeployment.embeddings": embeddings_str,
            }

            with self.dgraph_txn() as txn:
                mutation = txn.create_mutation(set_obj=mutation_data)
                response = txn.mutate(mutation=mutation, commit_now=False)
                self.logger.info(f"Successfully inserted embeddings for contract {uid}")
                return response
        except Exception as e:
            self.logger.exception(
                f"Failed to insert embeddings for contract {uid}: {str(e)}"
            )
            raise

    def get_contracts_count(self, enriched: bool = None) -> int:
        """
        Gets the total count of contracts in the database

        Args:
          enriched: If True, count only enriched contracts. If False, count only non-enriched. If None, count all.

        Returns:
          The total number of contracts
        """
        if enriched is None:
            # Count all contracts
            filter_clause = "eq(ContractDeployment.verified_source, true)"
        elif enriched:
            # Count only enriched contracts
            filter_clause = "eq(ContractDeployment.verified_source, true) AND has(ContractDeployment.description)"
        else:
            # Count only non-enriched contracts
            filter_clause = "eq(ContractDeployment.verified_source, true) AND NOT has(ContractDeployment.description)"

        query = f"""
        {{
          contractCount(func: type(ContractDeployment)) @filter({filter_clause}) {{
            count(uid)
          }}
        }}
        """

        with self.dgraph_txn(read_only=True) as txn:
            try:
                response = txn.query(query).json
                response = json.loads(response)
                count = (
                    response["contractCount"][0]["count"]
                    if response["contractCount"]
                    else 0
                )
                self.logger.info(
                    f"Total {'enriched' if enriched else 'non-enriched' if enriched is False else ''} contracts: {count}"
                )
                return count
            except Exception as e:
                self.logger.exception("Failed to get contracts count")
                raise

    def vector_search(
        self, query: str, limit: int = 5) -> list[dict]:
        """
        Performs vector similarity search on contracts using natural language query

        Args:
            query: Natural language search query
            limit: Maximum number of results to return

        Returns:
            List of similar contracts with metadata
        """
        try:
            # Convert query to embedding vector
            query_embedding = self.embedding_model.embed_query(query)

            # Format the vector for Dgraph query as a properly quoted JSON string
            vector_str = json.dumps(query_embedding)

            # Construct Dgraph vector similarity query using correct similar_to syntax
            # Syntax: similar_to(predicate, topK, "vector") - vector must be quoted
            dgraph_query = f"""
            {{
                similar_contracts(func: similar_to(ContractDeployment.embeddings, {limit}, "{vector_str}")) @filter(has(ContractDeployment.embeddings)) {{
                    uid
                    ContractDeployment.contract
                    ContractDeployment.block
                    ContractDeployment.storage_protocol
                    ContractDeployment.storage_address
                    ContractDeployment.experimental
                    ContractDeployment.solc_version
                    ContractDeployment.verified_source
                    ContractDeployment.verified_source_code
                    ContractDeployment.name
                    ContractDeployment.description
                    ContractDeployment.functionality_classification
                    ContractDeployment.application_domain
                    ContractDeployment.security_risks_description
                }}
            }}
            """

            with self.dgraph_txn(read_only=True) as txn:
                response = txn.query(dgraph_query).json
                response = json.loads(response)

                results = response.get("similar_contracts", [])
                self.logger.info(
                    f"Vector search found {len(results)} similar contracts for query: {query}"
                )
                return results

        except Exception as e:
            self.logger.error(f"Vector search failed for query '{query}': {e}")
            raise

    def close(self) -> None:
        """
        Closes the client stub
        """
        self.client_stub.close()
        self.logger.info("Client stub closed")


def main() -> None:
    client = None
    try:
        client = DgraphClient()
        all_unenriched = []
        batch_size = 50
        offset = 0

        while True:
            batch = client.get_contracts(
                batch_size=batch_size, offset=offset, enriched=False
            )
            if not batch:
                break
            all_unenriched.extend(batch)
            offset += batch_size

        write_file(all_unenriched, "unenriched_contracts.json")

        # Retrieve all enriched contracts in pages until empty
        all_enriched = []
        batch_size = 50
        offset = 0

        while True:
            batch = client.get_contracts(
                batch_size=batch_size, offset=offset, enriched=True
            )
            if not batch:
                break
            all_enriched.extend(batch)
            offset += batch_size

        result = all_enriched

        # Save results to file
        write_file(result, "retrieved_enriched_contracts.json")
    except Exception as e:
        logger.error(f"An error occurred in the main process: {str(e)}")
    finally:
        if client:
            client.close()
            # Test get single contract by uid using one of the retrieved UIDs
            try:
                # assume last `result` was the enriched contracts query
                client = DgraphClient()
                contracts_list = result
                if contracts_list:
                    test_uid = contracts_list[0]["uid"]
                    single_data = client.get_contract_by_uid(test_uid)
                    write_file(single_data, f"contract_{test_uid}.json")
                    logger.info(
                        f"Wrote single contract {test_uid} to contract_{test_uid}.json"
                    )
                else:
                    logger.warning("No contracts available to test get_contract_by_uid")
            except Exception as e:
                logger.error(f"Failed to test get_contract_by_uid: {e}")
            finally:
                client.close()


if __name__ == "__main__":
    main()
