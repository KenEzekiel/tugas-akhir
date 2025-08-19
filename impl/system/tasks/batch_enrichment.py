import asyncio
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

from langchain_huggingface import HuggingFaceEmbeddings
from src.core.data_access.dgraph_client import DgraphClient
from src.core.data_processing.llm_enrichment import ParallelSemanticEnricher
from src.utils.logger import logger


@contextmanager
def timer(operation_name: str):
    """Context manager for timing operations."""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        timer_logger = logger.getChild("Timer")
        timer_logger.info(f"{operation_name} completed in {elapsed_time:.2f}s")


@dataclass
class EnrichmentConfig:
    """Configuration for batch enrichment process."""

    batch_size: int = 10
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    device: str = "cpu"
    normalize_embeddings: bool = True


class BatchEnricher:
    """Handles batch enrichment of smart contracts with semantic analysis and embeddings."""

    def __init__(self, config: EnrichmentConfig):
        self.config = config
        self.dgraph = DgraphClient()
        self.enricher = ParallelSemanticEnricher()
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=config.embedding_model_name,
            model_kwargs={"device": config.device},
            encode_kwargs={"normalize_embeddings": config.normalize_embeddings},
        )
        self.dictionary = {
            # Standards
            "erc-20": "The standard for fungible tokens, representing interchangeable assets. Requires functions like transfer, approve, and balanceOf",
            "erc-721": "The standard for non-fungible tokens (NFTs), representing unique assets. Requires functions like ownerOf and safeTransferFrom",
            "erc-721a": "An optimized version of ERC-721 for significantly cheaper gas costs when minting multiple NFTs in a single transaction",
            "erc-1155": "A multi-token standard that can manage fungible, non-fungible, and semi-fungible tokens in a single contract",
            "erc-4626": "The Tokenized Vault standard. Provides a standard API for yield-bearing vaults that use a single underlying ERC-20 token",
            "erc-2981": "The NFT Royalty Standard. Provides a universal way to retrieve royalty payment information for an NFT",
            "erc-6551": "The Token Bound Accounts standard. Allows every NFT to own its own smart contract wallet, enabling it to hold assets and interact with dApps",
            "eip-712": "The standard for hashing and signing typed structured data, allowing for human-readable messages in wallets",
            "erc-165": "The Standard Interface Detection. Allows contracts to publish the interfaces they support",
            "eip-1967": "The Standard Proxy Storage Slots. Defines specific storage slots to store the logic address and admin address for transparent and UUPS proxies",
            "eip-1822": "The Universal Upgradeable Proxy Standard (UUPS). The standard that defines the UUPS upgradeable proxy pattern",
            "eip-2535": "The Diamond Standard. A modular smart contract system where a proxy delegates calls to multiple implementation contracts (facets)",
            "eip-2771": "The Secure Gasless Transactions standard. A system for accepting transactions where a third-party forwarder pays for gas on behalf of the user",
            "erc-4337": "The Account Abstraction standard. Allows for smart contract wallets with advanced features, executed via a decentralized mempool of UserOperations",
            # Design Patterns
            "proxy_transparent": "An upgradeable proxy pattern where logic for admins and users is separated into the proxy contract to avoid function selector clashes",
            "proxy_uups": "An upgradeable proxy pattern (EIP-1822) where the upgrade logic resides in the implementation contract itself, saving deployment gas",
            "diamond": "A modular contract composed of a proxy delegating calls to multiple facet implementation contracts, allowing for granular upgrades",
            "factory": "A contract whose primary purpose is to deploy other clone contracts, often using create or create2",
            "singleton": "A single, unique instance of a contract that serves as a shared resource or registry for an entire protocol",
            "access_control_ownable": "A simple permission model where a single owner address has special privileges, typically via onlyOwner modifiers",
            "access_control_role_based": "A complex permission model where different addresses are assigned specific roles with different rights",
            "reentrancy_guard": "A mechanism, typically a modifier (nonReentrant), to prevent a contract from being called again before its initial function call is complete",
            "checks_effects_interactions": "A code-structuring pattern where state variable checks are performed first, followed by updates to state (effects), and finally calls to external contracts (interactions)",
            "pull_over_push_withdrawal": "A pattern for handling withdrawals where users must call a withdraw function to pull funds, rather than the contract pushing funds to them, to mitigate certain security risks",
            "timelock": "A mechanism that enforces a mandatory delay between when an action is proposed and when it can be executed",
            "library": "A stateless contract containing reusable code that is called via DELEGATECALL by other contracts to save gas and avoid code duplication",
            "commit_reveal": "A two-step process to prevent front-running where a user first submits a hash of their action (commit) and later submits the action itself (reveal)",
            # Functionalities
            "token_transfer": "Performs core token actions like managing balances and handling transfers",
            "token_minting": "Contains logic for creating new tokens",
            "token_burning": "Contains logic for destroying existing tokens",
            "pausable": "Contains logic to pause and unpause contract functions, halting activity",
            "upgradable": "Contains logic to change the contract's implementation code, typically via a proxy",
            "signature_verification": "Verifies user signatures to authorize actions, often for gasless transactions",
            "staking": "Allows users to lock up assets to earn rewards",
            "vesting": "Locks assets for a period and releases them incrementally over time",
            "escrow": "Holds and locks assets, releasing them only when specific, predefined conditions are met",
            "payment_splitter": "Distributes incoming funds among a predefined set of payees according to specific shares",
            "financial_calculations_amm": "Performs calculations for an Automated Market Maker (e.g., swap prices)",
            "financial_calculations_interest_rate": "Contains logic for calculating interest rates for lending/borrowing",
            "onchain_voting": "Contains logic for proposal submission, vote counting, and determining quorum",
            "data_registry": "Functions as an on-chain key-value store or directory",
            "offchain_data_bridge": "Interacts with an oracle or cross-chain bridge to use external data",
            "randomness": "Consumes a source of on-chain or off-chain randomness (e.g., Chainlink VRF)",
            # Application Domains
            "defi_lending": "Protocols for lending and borrowing crypto assets (e.g., Aave, Compound)",
            "defi_dex": "Protocols for peer-to-peer asset trading, typically using an AMM (e.g., Uniswap, Curve)",
            "defi_stablecoin": "Contracts that issue and manage a token pegged to a stable value (e.g., MakerDAO, Frax)",
            "defi_derivatives": "Protocols for creating and trading synthetic assets, options, or futures",
            "defi_yield_aggregator": "Protocols that automatically move user funds to maximize yield (e.g., Yearn Finance)",
            "defi_liquid_staking": "Protocols that issue a liquid staking token (LST) for staked assets (e.g., Lido)",
            "nft_collection": "The core contract for an NFT project, managing minting, ownership, and metadata",
            "nft_marketplace": "A platform for listing, bidding on, and trading various NFTs (e.g., OpenSea Seaport)",
            "nft_infrastructure": "A protocol or tool that provides services for the NFT ecosystem",
            "governance_dao": "The core logic for a Decentralized Autonomous Organization, handling proposals and voting",
            "governance_treasury": "A contract for managing a community's funds, often a multi-sig wallet (e.g., Gnosis Safe)",
            "gaming_metaverse_game_logic": "Contains the core rules, state, and interactions for an on-chain game",
            "gaming_metaverse_virtual_assets": "Manages in-game items, currency, or virtual land",
            "identity_social_decentralized_id": "Manages decentralized identifiers (DIDs) and credentials",
            "identity_social_social_graph": "Creates a decentralized graph of user profiles and connections (e.g., Lens Protocol)",
            "infrastructure_oracle": "Provides external, real-world data (like asset prices) to the blockchain",
            "infrastructure_bridge": "Facilitates the transfer of assets or data between different blockchain networks",
            "infrastructure_naming_service": "Maps human-readable names to Ethereum addresses (e.g., ENS)",
            "infrastructure_storage": "Interacts with decentralized storage networks (e.g., Arweave, Filecoin)",
            "depin": "A protocol for Decentralized Physical Infrastructure Networks, which use token incentives to coordinate real-world services (e.g., Helium, Hivemapper)",
            "rwa_asset_tokenization": "Contracts that represent ownership of real-world assets on the blockchain",
            "utility_general_purpose": "A generic building block or tool whose application is not specific to any single domain",
        }

    def _create_contract_text(self, contract: Dict[str, Any]) -> str:
        """Create a text representation of contract for embedding."""
        description = contract.get("ContractDeployment.description", "")
        functionality = contract.get("ContractDeployment.functionalities", [])
        standards = contract.get("ContractDeployment.standards", [])
        patterns = contract.get("ContractDeployment.patterns", [])
        domain = contract.get("ContractDeployment.application_domain", "")
        security = contract.get("ContractDeployment.security_risks_description", "")

        # Helper function to format tags with descriptions
        def format_tags_with_descriptions(tags, tag_type=""):
            if not tags:
                return ""

            formatted_tags = []
            for tag in tags:
                if tag in self.dictionary:
                    formatted_tags.append(f"{tag} ({self.dictionary[tag]})")
                else:
                    formatted_tags.append(tag)

            return " ".join(formatted_tags)

        # Format each category with descriptions
        functionality_text = format_tags_with_descriptions(
            functionality, "functionalities"
        )
        standards_text = format_tags_with_descriptions(standards, "standards")
        patterns_text = format_tags_with_descriptions(patterns, "patterns")

        # Format domain with description if available
        domain_text = domain
        if domain and domain in self.dictionary:
            domain_text = f"{domain} ({self.dictionary[domain]})"

        return f"description: {description} \nfunctionalities: {functionality_text} \nstandards: {standards_text} \npatterns: {patterns_text} \napplication_domain: {domain_text} \nsecurity_risks_description: {security}"

    def _prepare_embedding_data(
        self, contracts: List[Dict[str, Any]]
    ) -> tuple[List[str], List[str], List[Dict[str, str]]]:
        """Prepare data for embedding generation."""
        texts = []
        ids = []
        metadatas = []

        for contract in contracts:
            # Use stable contract ID
            contract_id = contract.get("uid", "")
            # if contract_id is None or contract_id == "":
            #     logger.warning(f"Contract missing ID: {contract}")
            #     continue

            text = self._create_contract_text(contract)
            texts.append(text)
            ids.append(contract_id)
            metadatas.append({"contract_id": contract_id})

        return texts, ids, metadatas

    async def _process_embeddings(self, contracts: List[Dict[str, Any]]) -> None:
        """Process and store embeddings for contracts."""
        if not contracts:
            return

        try:
            texts, ids, metadatas = self._prepare_embedding_data(contracts)

            if not texts:
                logger.warning("No valid texts found for embedding generation")
                return

                # Measure embedding generation time with detailed metrics
            total_chars = sum(len(text) for text in texts)

            with timer(
                f"Embedding generation ({len(texts)} docs, {total_chars} chars)"
            ):
                embeddings = self.embedding_model.embed_documents(texts)

            # Store embeddings in Dgraph
            for contract, embedding in zip(contracts, embeddings):
                try:
                    contract_id = contract.get("uid")

                    if contract_id:
                        self.dgraph.insert_embeddings(contract_id, embedding)
                    else:
                        logger.warning("Contract missing UID")
                except Exception as e:
                    logger.error(
                        f"Failed to insert embedding for contract UID {contract_id}: {str(e)}"
                    )
                    # Continue with other contracts even if one fails

        except Exception as e:
            logger.error(f"Error processing embeddings: {str(e)}")

    async def _process_batch(self, contracts: List[Dict[str, Any]]) -> int:
        """Process a single batch of contracts."""
        if not contracts:
            return 0

        try:
            # Enrich contracts with semantic analysis
            enriched_contracts = await self.enricher.process_contracts(contracts)

            if enriched_contracts:
                # Update contracts in Dgraph
                self.dgraph.mutate(enriched_contracts)
                logger.info(f"Enriched and stored {len(enriched_contracts)} contracts")

                # Process embeddings
                await self._process_embeddings(enriched_contracts)

                return len(enriched_contracts)
            else:
                logger.warning("No contracts were enriched in this batch")
                return 0

        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            return 0

    async def enrich_new_contracts(self) -> int:
        """Enrich all contracts that haven't been enriched yet."""
        total_processed = 0

        while True:
            try:
                contracts = self.dgraph.get_contracts(
                    self.config.batch_size, enriched=False
                )

                if not contracts:
                    logger.info("No more contracts to enrich")
                    break

                processed_count = await self._process_batch(contracts)
                total_processed += processed_count

                logger.info(f"Total contracts processed: {total_processed}")

            except Exception as e:
                logger.error(f"Error in enrich_new_contracts loop: {str(e)}")
                break

        return total_processed

    async def update_enriched_contracts(self) -> int:
        """Update contracts that have already been enriched."""
        total_processed = 0

        try:
            contracts_count = self.dgraph.get_contracts_count(enriched=True)
            logger.info(f"Found {contracts_count} enriched contracts to update")

            for i in range(0, contracts_count, self.config.batch_size):
                try:
                    contracts = self.dgraph.get_contracts(
                        self.config.batch_size, offset=i, enriched=True
                    )

                    processed_count = await self._process_batch(contracts)
                    total_processed += processed_count

                    logger.info(
                        f"Updated batch {i // self.config.batch_size + 1}, total processed: {total_processed}"
                    )

                except Exception as e:
                    logger.error(f"Error processing batch at offset {i}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error in update_enriched_contracts: {str(e)}")

        return total_processed


async def batch_enrichment(batch_size: int = 10, update: bool = False) -> int:
    """
    Main function to run batch enrichment.

    Args:
        batch_size: Number of contracts to process in each batch
        update: If True, update already enriched contracts; otherwise enrich new contracts

    Returns:
        Total number of contracts processed
    """
    config = EnrichmentConfig(batch_size=batch_size)
    enricher = BatchEnricher(config)

    try:
        if update:
            logger.info("Starting update of enriched contracts...")
            return await enricher.update_enriched_contracts()
        else:
            logger.info("Starting enrichment of new contracts...")
            return await enricher.enrich_new_contracts()

    except Exception as e:
        logger.error(f"Fatal error in batch_enrichment: {str(e)}")
        return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch enrichment for contracts")
    parser.add_argument(
        "--update", action="store_true", help="Update already enriched contracts"
    )
    parser.add_argument(
        "--batch-size", type=int, default=10, help="Batch size for enrichment"
    )
    args = parser.parse_args()

    try:
        total_processed = asyncio.run(
            batch_enrichment(batch_size=args.batch_size, update=args.update)
        )
        logger.info(
            f"Batch enrichment completed. Total contracts processed: {total_processed}"
        )
    except KeyboardInterrupt:
        logger.info("Batch enrichment interrupted by user")
    except Exception as e:
        logger.error(f"Batch enrichment failed: {str(e)}")
        exit(1)
