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
        Your primary task is to analyze the provided smart contract source code and generate a single, minified JSON object as your response. Your analysis must be precise, objective, and strictly inferred from the provided code.

        ## Instructions:

        Analyze the smart contract code provided in `contract_data` and generate a single, valid, minified JSON object with the following schema. For keys requiring a list (`standards`, `patterns`, `functionalities`), only include the deductions that are clearly evident in the contract's code through inheritance, function signatures, or explicit implementation. Only pick options in the options provided, not actual code.
        
        The source code is a flattened source code file, so imports are already inserted into the source code. You should analyze the code of the main contract, usually after the imported contracts.

        ### JSON Schema:

        -   `description`: (String) A 3-4 sentence high-level summary. Clearly state the contract's identity, its main purpose and role in the system, what it does, and how it interacts with users or other contracts.
        -   `standards`: (List of Strings) A list of all ERC/EIP standards the contract adheres to. Only pick standards in the options provided.
        -   `patterns`: (List of Strings) A list of all high-level design patterns used to build the contract. Only pick patterns in the options provided.
        -   `functionalities`: (List of Strings) A list of granular tags for specific jobs the contract performs. Only pick functionalities in the options provided.
        -   `application_domain`: (String) The single most evident application domain for the contract.
        -   `security_risks_description`: (String) A 2-3 sentence description of potential security risks specific to the contract's design or function, avoiding generic warnings.

        ---

        ### Key Definitions and Options:

        #### **Standards** (`standards`)

        *Pick all that apply. Infer from interface IDs, inheritance, or function signatures.*

        **Token Standards:**
        -   `erc-20`: The standard for fungible tokens, representing interchangeable assets. Requires functions like `transfer`, `approve`, and `balanceOf`.
        -   `erc-721`: The standard for non-fungible tokens (NFTs), representing unique assets. Requires functions like `ownerOf` and `safeTransferFrom`.
        -   `erc-721a`: An optimized version of ERC-721 for significantly cheaper gas costs when minting multiple NFTs in a single transaction.
        -   `erc-1155`: A multi-token standard that can manage fungible, non-fungible, and semi-fungible tokens in a single contract.
        -   `erc-4626`: The "Tokenized Vault" standard. Provides a standard API for yield-bearing vaults that use a single underlying ERC-20 token.

        **NFT-Related Standards:**
        -   `erc-2981`: The "NFT Royalty Standard." Provides a universal way to retrieve royalty payment information for an NFT.
        -   `erc-6551`: The "Token Bound Accounts" standard. Allows every NFT to own its own smart contract wallet, enabling it to hold assets and interact with dApps.

        **Utility & Architecture Standards:**
        -   `eip-712`: The standard for hashing and signing typed structured data, allowing for human-readable messages in wallets.
        -   `erc-165`: The "Standard Interface Detection." Allows contracts to publish the interfaces they support (e.g., `supportsInterface(0x80ac58cd)` for ERC-721).
        -   `eip-1967`: The "Standard Proxy Storage Slots." Defines specific storage slots to store the logic address and admin address for transparent and UUPS proxies.
        -   `eip-1822`: The "Universal Upgradeable Proxy Standard (UUPS)." The standard that defines the UUPS upgradeable proxy pattern.
        -   `eip-2535`: The "Diamond Standard." A modular smart contract system where a proxy delegates calls to multiple implementation contracts ("facets").
        -   `eip-2771`: The "Secure Gasless Transactions" standard. A system for accepting transactions where a third-party forwarder pays for gas on behalf of the user.
        -   `erc-4337`: The "Account Abstraction" standard. Allows for smart contract wallets with advanced features, executed via a decentralized mempool of `UserOperations`.

        #### **Design Patterns** (`patterns`)

        *Pick all that apply. Identify from contract structure, inheritance, or logic.*

        **Upgradability Patterns:**
        -   `proxy_transparent`: An upgradeable proxy pattern where logic for admins and users is separated into the proxy contract to avoid function selector clashes.
        -   `proxy_uups`: An upgradeable proxy pattern (EIP-1822) where the upgrade logic resides in the implementation contract itself, saving deployment gas.
        -   `diamond`: A modular contract composed of a proxy delegating calls to multiple "facet" implementation contracts, allowing for granular upgrades.

        **Creational Patterns:**
        -   `factory`: A contract whose primary purpose is to deploy other "clone" contracts, often using `create` or `create2`.
        -   `singleton`: A single, unique instance of a contract that serves as a shared resource or registry for an entire protocol (e.g., the ERC-4337 EntryPoint).

        **Security & Control Patterns:**
        -   `access_control_ownable`: A simple permission model where a single "owner" address has special privileges, typically via `onlyOwner` modifiers.
        -   `access_control_role_based`: A complex permission model where different addresses are assigned specific roles (e.g., `MINTER_ROLE`, `PAUSER_ROLE`) with different rights.
        -   `reentrancy_guard`: A mechanism, typically a modifier (`nonReentrant`), to prevent a contract from being called again before its initial function call is complete.
        -   `checks_effects_interactions`: A code-structuring pattern where state variable checks are performed first, followed by updates to state (effects), and finally calls to external contracts (interactions).
        -   `pull_over_push_withdrawal`: A pattern for handling withdrawals where users must call a `withdraw` function to pull funds, rather than the contract pushing funds to them, to mitigate certain security risks.
        -   `timelock`: A mechanism that enforces a mandatory delay between when an action is proposed and when it can be executed.

        **State & Data Patterns:**
        -   `library`: A stateless contract containing reusable code that is called via `DELEGATECALL` by other contracts to save gas and avoid code duplication.
        -   `commit_reveal`: A two-step process to prevent front-running where a user first submits a hash of their action (commit) and later submits the action itself (reveal).

        #### **Functionalities** (`functionalities`)

        *Pick all options that apply. This is about *what* the contract does.*

        **Token Actions:**
        -   `token_transfer`: Performs core token actions like managing balances and handling transfers.
        -   `token_minting`: Contains logic for creating new tokens.
        -   `token_burning`: Contains logic for destroying existing tokens.

        **Security & Control:**
        -   `pausable`: Contains logic to pause and unpause contract functions, halting activity.
        -   `upgradable`: Contains logic to change the contract's implementation code, typically via a proxy.
        -   `signature_verification`: Verifies user signatures to authorize actions, often for gasless transactions (e.g., `permit`).

        **Financial Mechanisms:**
        -   `staking`: Allows users to lock up assets to earn rewards.
        -   `vesting`: Locks assets for a period and releases them incrementally over time.
        -   `escrow`: Holds and locks assets, releasing them only when specific, predefined conditions are met.
        -   `payment_splitter`: Distributes incoming funds among a predefined set of payees according to specific shares.
        -   `financial_calculations_amm`: Performs calculations for an Automated Market Maker (e.g., swap prices).
        -   `financial_calculations_interest_rate`: Contains logic for calculating interest rates for lending/borrowing.

        **Governance & Data:**
        -   `onchain_voting`: Contains logic for proposal submission, vote counting, and determining quorum.
        -   `data_registry`: Functions as an on-chain key-value store or directory.
        -   `offchain_data_bridge`: Interacts with an oracle or cross-chain bridge to use external data.
        -   `randomness`: Consumes a source of on-chain or off-chain randomness (e.g., Chainlink VRF).

        #### **Application Domain** (`application_domain`)

        *Pick only the ONE most evident domain.*

        -   `defi_lending`: Protocols for lending and borrowing crypto assets (e.g., Aave, Compound).
        -   `defi_dex`: Protocols for peer-to-peer asset trading, typically using an AMM (e.g., Uniswap, Curve).
        -   `defi_stablecoin`: Contracts that issue and manage a token pegged to a stable value (e.g., MakerDAO, Frax).
        -   `defi_derivatives`: Protocols for creating and trading synthetic assets, options, or futures.
        -   `defi_yield_aggregator`: Protocols that automatically move user funds to maximize yield (e.g., Yearn Finance).
        -   `defi_liquid_staking`: Protocols that issue a liquid staking token (LST) for staked assets (e.g., Lido).
        -   `nft_collection`: The core contract for an NFT project, managing minting, ownership, and metadata.
        -   `nft_marketplace`: A platform for listing, bidding on, and trading various NFTs (e.g., OpenSea Seaport).
        -   `nft_infrastructure`: A protocol or tool that provides services for the NFT ecosystem.
        -   `governance_dao`: The core logic for a Decentralized Autonomous Organization, handling proposals and voting.
        -   `governance_treasury`: A contract for managing a community's funds, often a multi-sig wallet (e.g., Gnosis Safe).
        -   `gaming_metaverse_game_logic`: Contains the core rules, state, and interactions for an on-chain game.
        -   `gaming_metaverse_virtual_assets`: Manages in-game items, currency, or virtual land.
        -   `identity_social_decentralized_id`: Manages decentralized identifiers (DIDs) and credentials.
        -   `identity_social_social_graph`: Creates a decentralized graph of user profiles and connections (e.g., Lens Protocol).
        -   `infrastructure_oracle`: Provides external, real-world data (like asset prices) to the blockchain.
        -   `infrastructure_bridge`: Facilitates the transfer of assets or data between different blockchain networks.
        -   `infrastructure_naming_service`: Maps human-readable names to Ethereum addresses (e.g., ENS).
        -   `infrastructure_storage`: Interacts with decentralized storage networks (e.g., Arweave, Filecoin).
        -   `depin`: A protocol for Decentralized Physical Infrastructure Networks, which use token incentives to coordinate real-world services (e.g., Helium, Hivemapper).
        -   `rwa_asset_tokenization`: Contracts that represent ownership of real-world assets on the blockchain.
        -   `utility_general_purpose`: A generic building block or tool whose application is not specific to any single domain.

        ---

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
            # preprocessed_contract = await self.preprocess_llm(contract_data)
            # result = await chain.ainvoke({"contract_data": preprocessed_contract})
            result = await chain.ainvoke({"contract_data": contract_data})

            result = {
                f"ContractDeployment.{key}": value for key, value in result.items()
            }
            result["uid"] = contract_data["uid"]
            result["id"] = contract_data["ContractDeployment.id"]

            self.logger.info(
                f"Enrichment process completed successfully for UID: {contract_data['uid']} ID: {contract_data['ContractDeployment.id']}"
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
        if hasattr(result, "content"):
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
