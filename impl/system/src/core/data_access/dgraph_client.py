import json
import pydgraph
import hashlib
from src.utils.logger import logger
from src.utils.file import write_file
from contextlib import contextmanager
from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np


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

    def generate_contract_id(self, contract_data: dict) -> str:
        """
        Generates a reproducible ID for a ContractDeployment based on its unique characteristics.

        The ID is generated from:
        - Contract address
        - Block number
        - Storage protocol
        - Storage address
        - Experimental flag
        - Solc version
        - Verified source flag
        - Verified source code hash

        Args:
            contract_data: Dictionary containing contract deployment data

        Returns:
            A reproducible string ID
        """
        try:
            # Extract the key fields that make a contract deployment unique
            contract_address = contract_data.get("ContractDeployment.contract", "")
            block_number = contract_data.get("ContractDeployment.block", "")
            storage_protocol = contract_data.get(
                "ContractDeployment.storage_protocol", ""
            )
            storage_address = contract_data.get(
                "ContractDeployment.storage_address", ""
            )
            experimental = str(
                contract_data.get("ContractDeployment.experimental", False)
            )
            solc_version = contract_data.get("ContractDeployment.solc_version", "")
            verified_source = str(
                contract_data.get("ContractDeployment.verified_source", False)
            )

            # For verified source code, use a hash to keep ID manageable
            verified_source_code = contract_data.get(
                "ContractDeployment.verified_source_code", ""
            )
            source_code_hash = (
                hashlib.sha256(verified_source_code.encode()).hexdigest()[:16]
                if verified_source_code
                else ""
            )

            # Create a deterministic string representation
            id_string = f"{contract_address}|{block_number}|{storage_protocol}|{storage_address}|{experimental}|{solc_version}|{verified_source}|{source_code_hash}"

            # Generate SHA-256 hash and take first 16 characters for readability
            contract_id = hashlib.sha256(id_string.encode()).hexdigest()[:16]

            self.logger.debug(
                f"Generated contract ID: {contract_id} from data: {id_string[:100]}..."
            )
            return contract_id

        except Exception as e:
            self.logger.error(f"Failed to generate contract ID: {str(e)}")
            # Fallback: use contract address if available
            contract_address = contract_data.get(
                "ContractDeployment.contract", "unknown"
            )
            return hashlib.sha256(contract_address.encode()).hexdigest()[:16]

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
        Retrieves contracts

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
        ContractDeployment.id
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
        ContractDeployment.standards
        ContractDeployment.patterns
        ContractDeployment.functionalities
        ContractDeployment.application_domain
        ContractDeployment.security_risks_description
        ContractDeployment.embeddings
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

    def get_contract_by_id(self, contract_id: str) -> dict:
        """
        Retrieves a contract by its reproducible ID.

        Args:
            contract_id: The reproducible ID of the contract to retrieve.

        Returns:
            The Dgraph query response as a dict.
        """
        query = f"""
        {{
          contract(func: eq(ContractDeployment.id, "{contract_id}")) {{
            uid
            ContractDeployment.id
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
            ContractDeployment.standards
            ContractDeployment.patterns
            ContractDeployment.functionalities
            ContractDeployment.application_domain
            ContractDeployment.security_risks_description
            ContractDeployment.embeddings
          }}
        }}
        """
        with self.dgraph_txn(read_only=True) as txn:
            try:
                response = txn.query(query).json
                response = json.loads(response)["contract"]
                if response:
                    self.logger.info(f"Retrieved contract with ID {contract_id}")
                    return response[0]  # Return first match
                else:
                    self.logger.warning(f"No contract found with ID {contract_id}")
                    return {}
            except Exception as e:
                self.logger.exception(
                    f"Failed to retrieve contract with ID {contract_id}: {e}"
                )
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
      ContractDeployment.id
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
      ContractDeployment.standards
      ContractDeployment.patterns
      ContractDeployment.functionalities
      ContractDeployment.application_domain
      ContractDeployment.security_risks_description
      ContractDeployment.embeddings
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

    def insert_embeddings(self, contract_id: str, embeddings: list[float]) -> None:
        """
        Inserts embeddings for a contract into Dgraph

        Args:
            contract_id: The ID of the contract to update
            embeddings: List of embedding values to store
        """
        try:
            # Ensure embeddings are float32 values
            embeddings_float32 = [float(e) for e in embeddings]

            # Format embeddings as quoted JSON string for float32vector
            embeddings_str = json.dumps(embeddings_float32)

            mutation_data = {
                "ContractDeployment.id": contract_id,
                "ContractDeployment.embeddings": embeddings_str,
            }

            with self.dgraph_txn() as txn:
                mutation = txn.create_mutation(set_obj=mutation_data)
                response = txn.mutate(mutation=mutation, commit_now=False)
                self.logger.info(
                    f"Successfully inserted embeddings for contract {contract_id}"
                )
                return response
        except Exception as e:
            self.logger.exception(
                f"Failed to insert embeddings for contract {contract_id}: {str(e)}"
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

    def vector_search(self, query: str, limit: int = 5) -> list[dict]:
        """
        Performs vector similarity search on contracts using natural language query

        Args:
            query: Natural language search query
            limit: Maximum number of results to return

        Returns:
            List of similar contracts with metadata, each including cosine similarity
        """
        try:
            # Convert query to embedding vector
            query_embedding = self.embedding_model.embed_query(query)
            self.logger.info(f"Query embedding length: {len(query_embedding)}")

            # Format the vector for Dgraph query as a properly quoted JSON string
            vector_str = json.dumps(query_embedding)

            # Construct Dgraph vector similarity query using correct similar_to syntax
            # Syntax: similar_to(predicate, topK, "vector") - vector must be quoted
            dgraph_query = f"""
            {{
                similar_contracts(func: similar_to(ContractDeployment.embeddings, {limit}, \"{vector_str}\")) @filter(has(ContractDeployment.embeddings)) {{
                    uid
                    ContractDeployment.id
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
                    ContractDeployment.standards
                    ContractDeployment.patterns
                    ContractDeployment.functionalities
                    ContractDeployment.application_domain
                    ContractDeployment.security_risks_description
                    ContractDeployment.embeddings
                }}
            }}
            """

            with self.dgraph_txn(read_only=True) as txn:
                response = txn.query(dgraph_query).json
                response = json.loads(response)
                results = response.get("similar_contracts", [])

                # Calculate cosine similarity for each result
                for result in results:
                    emb = result.get("ContractDeployment.embeddings")
                    if emb is not None:
                        try:
                            # Handle both string and list types
                            if isinstance(emb, str):
                                emb_vec = np.array(json.loads(emb), dtype=np.float32)
                            elif isinstance(emb, list):
                                emb_vec = np.array(emb, dtype=np.float32)
                            else:
                                raise ValueError(
                                    f"Unexpected type for embeddings: {type(emb)}"
                                )
                            query_vec = np.array(query_embedding, dtype=np.float32)
                            # Compute cosine similarity
                            if (
                                np.linalg.norm(emb_vec) > 0
                                and np.linalg.norm(query_vec) > 0
                            ):
                                cosine_sim = float(
                                    np.dot(emb_vec, query_vec)
                                    / (
                                        np.linalg.norm(emb_vec)
                                        * np.linalg.norm(query_vec)
                                    )
                                )
                            else:
                                cosine_sim = 0.0
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to parse or compute cosine similarity: {e}"
                            )
                            cosine_sim = None
                    else:
                        cosine_sim = None
                    result["cosine_similarity"] = cosine_sim

                self.logger.info(
                    f"Vector search found {len(results)} similar contracts for query: {query}"
                )
                return results

        except Exception as e:
            self.logger.error(f"Vector search failed for query '{query}': {e}")
            raise

    def search_by_text_source_code(self, query: str, limit: int = 5) -> list[dict]:
        """
        Performs text search on contracts using literal text search

        Args:
            query: Text string to search for in contract fields
            limit: Maximum number of results to return

        Returns:
            List of contracts that match the text query
        """
        try:
            # Construct Dgraph query with text search
            # Use match for name (trigram index) and anyofterms for source code (term index)
            dgraph_query = f"""
            {{
                text_search(func: type(ContractDeployment), first: {limit}) 
                @filter(eq(ContractDeployment.verified_source, true) AND 
                (anyofterms(ContractDeployment.verified_source_code, "{query}"))) {{
                    uid
                    ContractDeployment.id
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
                    ContractDeployment.standards
                    ContractDeployment.patterns
                    ContractDeployment.functionalities
                    ContractDeployment.application_domain
                    ContractDeployment.security_risks_description
                    ContractDeployment.embeddings
                }}
            }}
            """

            with self.dgraph_txn(read_only=True) as txn:
                response = txn.query(dgraph_query).json
                response = json.loads(response)
                results = response.get("text_search", [])

                self.logger.info(
                    f"Text source code search found {len(results)} contracts for query: '{query}'"
                )
                return results

        except Exception as e:
            self.logger.error(
                f"Text source code search failed for query '{query}': {e}"
            )
            raise

    def search_by_text(self, query: str, limit: int = 5) -> list[dict]:
        """
        Performs text search on contracts using literal text search

        Args:
            query: Text string to search for in contract fields
            limit: Maximum number of results to return

        Returns:
            List of contracts that match the text query
        """
        try:
            # Construct Dgraph query with text search
            # Use anyofterms for name and source code (more flexible matching)
            # Use allofterms for other fields (more precise matching)
            dgraph_query = f"""
            {{
                text_search(func: type(ContractDeployment), first: {limit}) 
                @filter(eq(ContractDeployment.verified_source, true) AND 
                (anyoftext(ContractDeployment.description, "{query}") OR
                 anyofterms(ContractDeployment.standards, "{query}") OR
                 anyofterms(ContractDeployment.patterns, "{query}") OR
                 anyofterms(ContractDeployment.functionalities, "{query}") OR
                 anyoftext(ContractDeployment.application_domain, "{query}") OR
                 anyoftext(ContractDeployment.security_risks_description, "{query}"))) {{
                    uid
                    ContractDeployment.id
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
                    ContractDeployment.standards
                    ContractDeployment.patterns
                    ContractDeployment.functionalities
                    ContractDeployment.application_domain
                    ContractDeployment.security_risks_description
                    ContractDeployment.embeddings
                }}
            }}
            """

            with self.dgraph_txn(read_only=True) as txn:
                response = txn.query(dgraph_query).json
                response = json.loads(response)
                results = response.get("text_search", [])

                self.logger.info(
                    f"Text search found {len(results)} contracts for query: '{query}'"
                )
                return results

        except Exception as e:
            self.logger.error(f"Text search failed for query '{query}': {e}")
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
