import re
from dotenv import load_dotenv
import asyncio
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.chat_models import init_chat_model
from src.core.data_access.dgraph_client import DgraphClient
from src.utils.file import write_file
from src.utils.logger import logger
from src.utils.tokens import num_tokens_from_string

load_dotenv()

class SemanticEnricher:
  """
  Enriches smart contracts with semantic information using a language model
  """
  
  def __init__(self, model: str = "gpt-4o-mini", model_provider: str = "openai") -> None:
    
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
      - description: 2-3 sentence description of the contract, mainly the purpose of the contract, specific function of what the contract does.
      - functionality_classification: (Pick one, only write the picked key)
        - token_contracts:
          - token_contracts:erc-20: {{description: "Standard for fungible tokens, meaning each token is identical and interchangeable (e.g., cryptocurrencies like USDC or UNI)."}}
          - token_contracts:erc-721: {{description: "Standard for non-fungible tokens, meaning each token is unique and not interchangeable (e.g., digital art, collectibles like CryptoPunks)."}}
          - token_contracts:erc-1155: {{description: "A multi-token standard that allows for both fungible and non-fungible tokens within a single contract, offering greater efficiency."}}
        - library_contracts: {{description: "Reusable code modules that other smart contracts can call upon, promoting code efficiency and reducing redundancy."}}
        - proxy_contracts: {{description: "Contracts that delegate calls to an underlying implementation contract, enabling upgradeability of smart contracts without changing the contract address."}}
        - multisignature_wallets: {{description: "Contracts that require multiple pre-approved signatures to authorize a transaction, enhancing security for shared funds or critical operations."}}
        - name_services: {{description: "Smart contracts that map human-readable names (e.g., 'example.eth') to machine-readable blockchain addresses, simplifying interactions and enabling decentralized websites. Example: Ethereum Name Service (ENS)."}}
        - smart_wallets: {{description: "Wallets built as smart contracts, offering advanced features like social recovery, batch transactions, and multi-signature capabilities beyond basic external accounts."}}
      - application_domain: (Pick one, only write the picked key)
        - defi:
          - defi:lending_borrowing: {{description: "Protocols allowing users to lend out their crypto assets to earn interest, or borrow crypto by providing collateral. Examples include Aave and Compound."}}
          - defi:decentralized_exchanges: {{description: "Platforms for peer-to-peer cryptocurrency trading without the need for a central intermediary. Examples include Uniswap and SushiSwap."}}
          - defi:stablecoins: {{description: "Contracts that manage digital assets designed to maintain a stable value, often pegged to fiat currencies like USD. Examples include MakerDAO's DAI and Tether's USDT."}}
          - defi:yield_farming/liquidity_mining: {{description: "Protocols that incentivize users to provide liquidity to DeFi platforms by rewarding them with additional tokens."}}
          - defi:insurance: {{description: "Decentralized protocols offering coverage against various risks in the crypto space, such as smart contract hacks or stablecoin de-pegging."}}
        - gaming: {{description: "Smart contracts used for in-game assets (NFTs), game logic, virtual economies, and player interactions within blockchain-based games."}}
        - nft_marketplaces/collectibles: {{description: "Platforms that enable the creation, buying, selling, and management of Non-Fungible Tokens (NFTs), which represent unique digital or physical assets. Examples include OpenSea and Rarible."}}
        - gambling: {{description: "Decentralized applications for betting, lotteries, and other forms of gambling where outcomes are determined by smart contracts."}}
        - social: {{description: "Smart contracts that power decentralized social media platforms, identity management systems, and reputation protocols."}}
        - supply_chain: {{description: "Contracts used to track and verify goods, automate payments, and ensure transparency and traceability in supply chain processes."}}
        - voting/governance: {{description: "Smart contracts that enable decentralized autonomous organizations (DAOs) to make collective decisions, manage treasuries, and implement proposals."}}
        - identity_verification: {{description: "Protocols and contracts for secure, self-sovereign digital identity management and verification."}}
      - security_risks_description: 2-3 sentence description of the security risks of the contract, if any.

      
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
      
      self.logger.info(f"Enrichment process completed successfully for UID: {contract_data['uid']}")
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
    
    # with open("./data/retrieved_enriched_contracts.json", "r") as file:
    #   contracts = json.load(file)["allContractDeployments"]

    contracts = dgraph_client.get_contracts(enriched=False)
    
    parallel_enricher = ParallelSemanticEnricher()
    
    logger.info("Starting parallel enrichment process...")
    response = await parallel_enricher.process_contracts(contracts)
    
    logger.info("Parallel enrichment process completed successfully")

    # Write the enriched data to a JSON file
    write_file(response, "parallel_enriched_data.json")
    
    dgraph_client.mutate(response, commit_now=True)
    
    # enricher = SemanticEnricher()

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
