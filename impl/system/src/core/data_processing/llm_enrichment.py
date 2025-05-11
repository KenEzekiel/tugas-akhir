import re
from dotenv import load_dotenv
import asyncio
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.chat_models import init_chat_model
from system.src.core.data_access.dgraph_client import DgraphClient
from utils.file import write_file
from utils.logger import logger
from utils.tokens import num_tokens_from_string

load_dotenv()

class SemanticEnricher:
  """
  Enriches smart contracts with semantic information using a language model
  """
  
  def __init__(self, model: str = "deepseek-r1-distill-llama-70b", model_provider: str = "groq") -> None:
    
    self.logger = logger.getChild("SemanticEnricher")

    # Initialize LLM and parser
    try:
      self.llm = init_chat_model(model, model_provider=model_provider)
      self.parser = JsonOutputParser()
    except Exception as e:
      logger.error(f"Failed to initialize models: {str(e)}")
      raise

    # Prepare chat prompt template
    self.prompt = ChatPromptTemplate.from_template(
      """
      Analyze this smart contract and return JSON with:
      - functionality: 2-3 sentence description
      - domain: DeFi, NFT, DAO, or Gaming
      - security_risks: list of risks
      
      the smart contract given has some keywords truncated with this dictionary:
      - func: function
      - ret: return
      - rets: returns
      Data: {contract_data}
      """
    )

  async def enrich(self, contract_data: str) -> dict:
    """
    Asynchronously sends the contract data through the chain consisting of
    the prompt, language model, and output parser

    Args:
      contract_data (str): Raw data for the smart contract

    Returns:
      dict: Parsed JSON response with enrichment details
    """
    # Create the processing chain
    chain = self.prompt | self.llm | self.parser
    self.logger.info("Starting enrichment process...")
    result = {}
    try:
      preprocessed_contract = self.preprocess(contract_data)
      result = await chain.ainvoke({"contract_data": preprocessed_contract})
      
      result = {f"ContractDeployment.{key}": value for key, value in result.items()}
      result["uid"] = contract_data["uid"]
      
      self.logger.info(f"Enrichment process completed successfully for UID: {contract_data["uid"]}")
    except Exception as e:
      self.logger.error(f"Error during enrichment: {str(e)}")
      raise
    finally:
      return result
  
  def preprocess(self, contract: dict) -> dict:
    """
    Preprocesses the contract data

    Args:
      contract (dict): The contract data to preprocess

    Returns:
      dict: The preprocessed contract data
    """
    source = contract["ContractDeployment.verified_source_code"]
    prev_token_count = num_tokens_from_string(source, "cl100k_base")
    
     # Initial cleanup
    source = source.replace("\r", "").rstrip()
    
    # Remove verification headers and SPDX
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    source = re.sub(r'// SPDX-License-Identifier:.*\n', '', source)
    
    # Remove all comments
    source = re.sub(r'\/\*[\s\S]*?\*\/|\/\/.*', '', source)
    
    # Common pattern replacements
    replacements = [
        # Boilerplate contracts
        (r'contract Context \{[\s\S]*?\}', '// Context removed'),
        (r'contract Ownable [\s\S]*?emit OwnershipTransferred\(address\(0\), msgSender\);\s*\}', 
         '// Ownable implementation'),
        (r'library SafeMath \{[\s\S]*?\}', '// SafeMath library'),
        
        # Interfaces
        (r'interface IERC20 \{[\s\S]*?\}', '// IERC20 interface'),
        (r'interface IUniswapV2Factory \{[\s\S]*?\}', '// UniswapV2 interfaces'),
        (r'interface IUniswapV2Router02 \{[\s\S]*?\}', '// UniswapV2 router interface'),
        
        # Common syntax patterns
        (r'mapping (\(address => )?(\w+)\) private \w+;', r'// \1\2 mapping'),
        (r'pragma solidity \^?\d+\.\d+\.\d+;', '// Solidity version'),
        (r'using SafeMath for uint256;', '// SafeMath usage'),
        
        # Math operations (Solidity 0.8+ safe)
        (r'\.add\(', '+'),
        (r'\.sub\(', '-'),
        (r'\.mul\(', '*'),
        (r'\.div\(', '/'),
        
        # Reflection token patterns
        (r'mapping \(address => uint256\) private _rOwned;[\s\S]*?_tFeeTotal;',
         '// Reflection token mechanics'),
         
        # Address shortening
        (r'0x[a-fA-F0-9]{40}', lambda m: f'0x...{m.group(0)[-4:]}'),
        
        # Decimal notation
        (r'10\*\*(\d+)', r'e\1'),
        
        # Function compression
        (r'function \w+\(\) public pure returns \(\w+ memory\) \{[\s\S]*?return \w+;\s*\}',
         '// Standard accessor'),
         
        # Tax structure
        (r'_redisFeeOnBuy = \d+;[\s\S]*?_taxFeeOnSell = \d+;',
         '// Tax structure parameters')
    ]

    for pattern, replacement in replacements:
        source = re.sub(pattern, replacement, source)
    
    # Structural cleanup
    source = '\n'.join([line for line in source.split('\n') if line.strip()])
    source = re.sub(r'\n{3,}', '\n\n', source)
    
    token_count = num_tokens_from_string(source, "cl100k_base")
    self.logger.info(f"Preprocessing Data:\n Previous Token Count: {prev_token_count}\n After Token Count: {token_count}\n Token Count Difference: {token_count - prev_token_count}\n Percentage: {(token_count - prev_token_count) / prev_token_count * 100}")
    
    # Apply hard cap at 4000 tokens
    if token_count > 4000:
      source = source[:int(len(source) * (4000/token_count))]
      token_count = num_tokens_from_string(source, "cl100k_base")
      self.logger.info(f"Applied hard cap. New token count: {token_count}")
    
    contract["ContractDeployment.verified_source_code"] = source
    return contract
  

class ParallelSemanticEnricher:
  def __init__(self):
    self.enricher = SemanticEnricher()

  async def process_contracts(self, contracts):
    tasks = []
    for contract in contracts:
      tasks.append(self.enricher.enrich(contract))
      logger.info(f"Enriching contract with UID: {contract['uid']}")
    return await asyncio.gather(*tasks)
  

if __name__ == "__main__":

  async def main():
    dgraph_client = DgraphClient()
    
    with open("./data/retrieved_enriched_contracts.json", "r") as file:
      contracts = json.load(file)["allContractDeployments"]
    
    parallel_enricher = ParallelSemanticEnricher()
    
    logger.info("Starting parallel enrichment process...")
    response = await parallel_enricher.process_contracts(contracts)
    
    logger.info("Parallel enrichment process completed successfully")

    # Write the enriched data to a JSON file
    write_file(response, "parallel_enriched_data.json")
    
    dgraph_client.mutate(response, commit_now=True)
    
    enricher = SemanticEnricher()

    # try:
    #   enriched_data = []
    #   for contract in contracts:
    #     logger.info(f"Enriching contract with UID: {contract['uid']}")
    #     response = await enricher.enrich(contract)
    #     print("Enriched Data:", response)
    #     enriched_data.append(response)

    #   # Write the enriched data to a JSON file.
    #   write_file(enriched_data, "enriched_data.json")
    #   dgraph_client.mutate(enriched_data, commit_now=True)
    # except Exception as e:
    #   logger.error(f"Processing failed: {e}")

  asyncio.run(main())
