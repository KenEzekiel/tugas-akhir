import os
import json
import pydgraph
from utils.logger import logger
from utils.file import write_file
from contextlib import contextmanager


class DgraphClient:
  """
  Interface for interacting with Dgraph database
  """
  
  def __init__(self, host: str = 'localhost', port: int = 9081) -> None:
    self.logger = logger.getChild("DgraphClient")
    self.client_stub = pydgraph.DgraphClientStub(f"{host}:{port}")
    self.client = pydgraph.DgraphClient(self.client_stub)

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
    
  def get_contracts(self, batch_size: int = 5, enriched: bool = False) -> dict[str, str]:
    """
    Retrieves unenriched contracts without a semantic description
    
    Args:
      batch_size: Maximum number of results to return
    
    Returns:
      The Dgraph query response
    """
    query = f"""
    {{
      allContractDeployments(func: type(ContractDeployment), first:{batch_size}) 
      @filter(eq(ContractDeployment.verified_source, true) AND 
      {"" if enriched else "NOT"} has(ContractDeployment.functionality)) 
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
        ContractDeployment.functionality
        ContractDeployment.domain
        ContractDeployment.security_risks
      }}
    }}
    """
    with self.dgraph_txn(read_only=True) as txn:
      try:
        response = txn.query(query)
        self.logger.info(f"Retrieved {"" if enriched else "un"}enriched contracts")
        return response
      except Exception as e:
        self.logger.exception("Dgraph query failed")
        raise
      

  def mutate(self, mutation_data: dict[str, str], commit_now: bool = True) -> dict:
    """
    Performs a mutation (insert/update) in the database
    
    Args:
      mutation_data: A dictionary to be converted to JSON for the mutation.
      commit_now: Whether to commit the mutation immediately
    
    Returns:
      The mutation response
    """
    with self.dgraph_txn() as txn:
      try:
        mutation = txn.create_mutation(set_obj=mutation_data)
        response = txn.mutate(mutation=mutation, commit_now=commit_now)
        self.logger.info("Mutation successful")
        return response
      except Exception as e:
        self.logger.exception("Mutation failed")
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
    result = client.get_contracts(batch_size=10, enriched=False)

    # Save results to file
    json_data = json.loads(result.json)
    write_file(json_data, 'unenriched_contracts.json')
    
    result = client.get_contracts(batch_size=100, enriched=True)

    # Save results to file
    json_data = json.loads(result.json)
    write_file(json_data, 'retrieved_enriched_contracts.json')
  except Exception as e:
    logger.error(f"An error occurred in the main process: {str(e)}")
  finally:
    if client:
      client.close()

if __name__ == '__main__':
  main()
