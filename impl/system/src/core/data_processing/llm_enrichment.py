import re
from dotenv import load_dotenv
import asyncio
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

    def __init__(
        self, model: str = "gpt-4o-mini", model_provider: str = "openai"
    ) -> None:
        self.logger = logger.getChild("SemanticEnricher")

        # Initialize LLM and parser
        try:
            self.llm = init_chat_model(model, model_provider=model_provider)
            self.analysis_llm = init_chat_model(
                "gemini-2.5-flash-lite", model_provider="google_genai"
            )
            self.parser = JsonOutputParser()
        except Exception as e:
            logger.error(f"Failed to initialize models: {str(e)}")
            raise

        self.analyzer_prompt = ChatPromptTemplate.from_template(
            """
      You are an expert Solidity developer. Analyze the following Solidity source code provided in its entirety. Your task is to ignore boilerplate (like SafeMath, or simple libraries) and extract the core logic and intent of the contract(s).

      Create a structured text summary covering these key points:
      - **Project Name/Purpose:** What is the high-level goal of this contract? Use NatSpec comments like `@title` if available.
      - **Main Contract:** Which contract is the primary entry point?
      - **Inheritance Chain:** Show the full inheritance path (e.g., ContractA is ContractB, ContractB is ContractC).
      - **Core Functionality:** In plain English, describe the contract's main purpose. Does it mint tokens? Is it a proxy? Does it manage a DAO?
      - **Key Functions/Events:** List the constructor and any public or external functions defined in the main contract. Mention the most critical events that signal its core purpose (e.g., `Transfer`, `Mint`, `Upgrade`).

      Do not output JSON. Your output must be a clean, easy-to-read text summary.

      --- SOURCE CODE ---
      {contract_data}
      """
        )

        # Prepare chat prompt template
        self.prompt = ChatPromptTemplate.from_template(
            """
      You are an expert smart contract auditor and blockchain analyst. Your task is to analyze a given smart contract and return a single, minified JSON object based on its code. Your analysis must be precise and strictly derived from the provided contract data.

      Analyze this smart contract and return a single, minified JSON object with the following keys:
      - description: A 2-3 sentence description of the contract. Clearly state its main purpose and mention 1-2 key or unique functions that distinguish it from other contracts of its type.
      - functionality_classification: (Pick ONE that is most prominent, return as a JSON array of strings)
        - token_contracts:erc-20: {{description: "Standard for fungible tokens (e.g., cryptocurrencies like USDC or UNI)."}}
        - token_contracts:erc-721: {{description: "Standard for non-fungible tokens (e.g., digital art, collectibles)."}}
        - token_contracts:erc-1155: {{description: "Multi-token standard for both fungible and non-fungible tokens."}}
        - token_contracts:bep-20: {{description: "Standard for fungible tokens on BEP-20 chains."}}
        - library_contracts: {{description: "Reusable code modules that other contracts can call."}}
        - proxy_contracts: {{description: "Delegates calls to an implementation contract, enabling upgrades."}}
        - multisignature_wallets: {{description: "Requires multiple signatures to authorize a transaction."}}
        - name_services: {{description: "Maps human-readable names to blockchain addresses (e.g., ENS)."}}
        - smart_wallets: {{description: "Contract-based wallets with advanced features like social recovery."}}
      - application_domain: (Pick one that is most evident from the contract. If the specific domain is not clear, MUST select 'general_purpose'. Only write the picked key.)
        - defi:lending_borrowing: {{description: "Protocols for lending and borrowing crypto assets."}}
        - defi:decentralized_exchanges: {{description: "Peer-to-peer cryptocurrency trading platforms."}}
        - defi:stablecoins: {{description: "Contracts managing assets pegged to a stable value."}}
        - defi:yield_farming/liquidity_mining: {{description: "Protocols that reward users for providing liquidity."}}
        - defi:insurance: {{description: "Decentralized coverage against crypto-related risks."}}
        - gaming: {{description: "For in-game assets, logic, and virtual economies."}}
        - nft_marketplaces/collectibles: {{description: "Platforms for creating, buying, and selling NFTs."}}
        - gambling: {{description: "Decentralized applications for betting and lotteries."}}
        - social: {{description: "For decentralized social media, identity, or reputation systems."}}
        - supply_chain: {{description: "To track and verify goods and automate payments."}}
        - voting/governance: {{description: "For DAOs to make collective decisions."}}
        - identity_verification: {{description: "For self-sovereign digital identity management."}}
        - general_purpose: {{description: "The contract is a generic building block or its specific application is not clearly defined."}}
      - security_risks_description: A 2-3 sentence description of the potential security risks of the contract, focusing on vulnerabilities specific to its design or function.

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
            preprocessed_contract = await self.preprocess_llm(contract_data)
            result = await chain.ainvoke({"contract_data": preprocessed_contract})

            result = {
                f"ContractDeployment.{key}": value for key, value in result.items()
            }
            result["uid"] = contract_data["uid"]

            self.logger.info(
                f"Enrichment process completed successfully for UID: {contract_data['uid']}"
            )
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
        source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        source = re.sub(r"// SPDX-License-Identifier:.*\n", "", source)

        # Remove all comments
        source = re.sub(r"\/\*[\s\S]*?\*\/|\/\/.*", "", source)

        # Common pattern replacements
        replacements = [
            # Boilerplate contracts
            (r"contract Context \{[\s\S]*?\}", "// Context removed"),
            (
                r"contract Ownable [\s\S]*?emit OwnershipTransferred\(address\(0\), msgSender\);\s*\}",
                "// Ownable implementation",
            ),
            (r"library SafeMath \{[\s\S]*?\}", "// SafeMath library"),
            # Interfaces
            (r"interface IERC20 \{[\s\S]*?\}", "// IERC20 interface"),
            (r"interface IUniswapV2Factory \{[\s\S]*?\}", "// UniswapV2 interfaces"),
            (
                r"interface IUniswapV2Router02 \{[\s\S]*?\}",
                "// UniswapV2 router interface",
            ),
            # Common syntax patterns
            (r"mapping (\(address => )?(\w+)\) private \w+;", r"// \1\2 mapping"),
            (r"pragma solidity \^?\d+\.\d+\.\d+;", "// Solidity version"),
            (r"using SafeMath for uint256;", "// SafeMath usage"),
            # Math operations (Solidity 0.8+ safe)
            (r"\.add\(", "+"),
            (r"\.sub\(", "-"),
            (r"\.mul\(", "*"),
            (r"\.div\(", "/"),
            # Reflection token patterns
            (
                r"mapping \(address => uint256\) private _rOwned;[\s\S]*?_tFeeTotal;",
                "// Reflection token mechanics",
            ),
            # Address shortening
            (r"0x[a-fA-F0-9]{40}", lambda m: f"0x...{m.group(0)[-4:]}"),
            # Decimal notation
            (r"10\*\*(\d+)", r"e\1"),
            # Function compression
            (
                r"function \w+\(\) public pure returns \(\w+ memory\) \{[\s\S]*?return \w+;\s*\}",
                "// Standard accessor",
            ),
            # Tax structure
            (
                r"_redisFeeOnBuy = \d+;[\s\S]*?_taxFeeOnSell = \d+;",
                "// Tax structure parameters",
            ),
        ]

        for pattern, replacement in replacements:
            source = re.sub(pattern, replacement, source)

        # Structural cleanup
        source = "\n".join([line for line in source.split("\n") if line.strip()])
        source = re.sub(r"\n{3,}", "\n\n", source)

        token_count = num_tokens_from_string(source, "cl100k_base")
        self.logger.info(
            f"Preprocessing Data:\n Previous Token Count: {prev_token_count}\n After Token Count: {token_count}\n Token Count Difference: {token_count - prev_token_count}\n Percentage: {(token_count - prev_token_count) / prev_token_count * 100}"
        )

        # Apply hard cap at 4000 tokens
        if token_count > 4000:
            source = source[: int(len(source) * (4000 / token_count))]
            token_count = num_tokens_from_string(source, "cl100k_base")
            self.logger.info(f"Applied hard cap. New token count: {token_count}")

        contract["ContractDeployment.verified_source_code"] = source
        return contract

    async def preprocess_llm(self, contract: dict) -> dict:
        """
        Preprocesses the contract data for the LLM
        """
        source = contract["ContractDeployment.verified_source_code"]
        prev_token_count = num_tokens_from_string(source, "cl100k_base")

        analysis_chain = self.analyzer_prompt | self.analysis_llm

        result = await analysis_chain.ainvoke({"contract_data": source})
        
        # Ensure result is a string
        if hasattr(result, 'content'):
            result = result.content
        elif not isinstance(result, str):
            result = str(result)

        token_count = num_tokens_from_string(result, "cl100k_base")

        self.logger.info(
            f"Preprocessing Data:\n Previous Token Count: {prev_token_count}\n After Token Count: {token_count}\n Token Count Difference: {token_count - prev_token_count}\n Percentage: {(token_count - prev_token_count) / prev_token_count * 100}"
        )

        contract["ContractDeployment.verified_source_code"] = result

        return contract


class ParallelSemanticEnricher:
    def __init__(self):
        self.enricher = SemanticEnricher()

    async def process_contracts(self, contracts):
        tasks = []
        for contract in contracts:
            filtered_contract = {
                "uid": contract.get("uid"),
                "ContractDeployment.id": contract.get("ContractDeployment.id"),
                "ContractDeployment.storage_protocol": contract.get(
                    "ContractDeployment.storage_protocol"
                ),
                "ContractDeployment.storage_address": contract.get(
                    "ContractDeployment.storage_address"
                ),
                "ContractDeployment.experimental": contract.get(
                    "ContractDeployment.experimental"
                ),
                "ContractDeployment.solc_version": contract.get(
                    "ContractDeployment.solc_version"
                ),
                "ContractDeployment.verified_source": contract.get(
                    "ContractDeployment.verified_source"
                ),
                "ContractDeployment.verified_source_code": contract.get(
                    "ContractDeployment.verified_source_code"
                ),
                "ContractDeployment.name": contract.get("ContractDeployment.name"),
            }
            tasks.append(self.enricher.enrich(filtered_contract))
            logger.info(
                f"Enriching contract with ID: {contract['ContractDeployment.id']}"
            )
        return await asyncio.gather(*tasks)


if __name__ == "__main__":

    async def main():
        dgraph_client = DgraphClient()

        # with open("./data/retrieved_enriched_contracts.json", "r") as file:
        #   contracts = json.load(file)["allContractDeployments"]

        contracts = dgraph_client.get_contracts(enriched=True)

        parallel_enricher = ParallelSemanticEnricher()

        logger.info("Starting parallel enrichment process...")
        response = await parallel_enricher.process_contracts(contracts)

        logger.info("Parallel enrichment process completed successfully")

        # Write the enriched data to a JSON file
        write_file(response, "parallel_enriched_data.json")

        # dgraph_client.mutate(response, commit_now=True)

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
