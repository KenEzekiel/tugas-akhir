import re
from typing import TypedDict, List, Dict, Any, Optional
from dotenv import load_dotenv
import asyncio
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from langgraph_checkpoint.memory import MemorySaver
from system.src.core.data_access.dgraph_client import DgraphClient
from system.src.core.data_access.vectordb_client import VectorDBManager
from utils.file import write_file
from utils.logger import logger
from utils.tokens import num_tokens_from_string

load_dotenv()

class SmartContractAnalysisState(TypedDict):
    # Inputs
    source_code: str
    contract_id: Optional[str]  # To identify the contract later

    # Stage 1: Info Extraction
    extracted_infos: Optional[Dict[str, Any]]  # Raw facts from code
    parsing_errors: Optional[List[str]]

    # Stage 2: Insight Generation (LLM)
    generated_insights: Optional[Dict[str, Any]]  # Inferred knowledge
    insight_generation_errors: Optional[List[str]]

    # Stage 3: Schema/Ontology (LLM)
    populated_ontology: Optional[Dict[str, Any]]  # Populated schema instances
    ontology_population_errors: Optional[List[str]]

    # Stage 4: Data Augmentation
    augmented_data_for_embedding: Optional[List[Dict[str, Any]]]  # E.g., list of text chunks with metadata
    augmentation_errors: Optional[List[str]]

    # Stage 5: Embedding
    embeddings: Optional[List[List[float]]]
    embedding_errors: Optional[List[str]]

    # Final output or for storage
    final_processed_contract: Optional[Dict[str, Any]]  # Could combine key elements for storage

class AgentEnricher:
    """
    Enriches smart contracts using a multi-agent system powered by LangGraph
    """
    
    def __init__(self, model: str = "deepseek-r1-distill-llama-70b", model_provider: str = "groq") -> None:
        self.logger = logger.getChild("AgentEnricher")
        
        # Initialize LLM and parser
        try:
            self.llm = init_chat_model(model, model_provider=model_provider)
            self.parser = JsonOutputParser()
        except Exception as e:
            self.logger.error(f"Failed to initialize models: {str(e)}")
            raise

        # Initialize the workflow graph
        self.workflow = self._create_workflow()
        
        # Initialize database clients
        self.dgraph_client = DgraphClient()
        self.vector_db = VectorDBManager()

    def _create_workflow(self) -> StateGraph:
        """Creates and configures the LangGraph workflow"""
        workflow = StateGraph(SmartContractAnalysisState)
        
        # Add nodes
        workflow.add_node("INPUT", self._input_node)
        workflow.add_node("INFO_EXTRACTOR", self._info_extractor_node)
        workflow.add_node("INSIGHT_GENERATOR", self._insight_generator_node)
        workflow.add_node("SCHEMA_ONTOLOGY", self._schema_ontology_node)
        workflow.add_node("DATA_AUGMENTER", self._data_augmenter_node)
        workflow.add_node("EMBEDDER", self._embedder_node)
        workflow.add_node("OUTPUT_FORMATTER", self._output_formatter_node)
        
        # Define edges
        workflow.set_entry_point("INPUT")
        workflow.add_edge("INPUT", "INFO_EXTRACTOR")
        workflow.add_edge("INFO_EXTRACTOR", "INSIGHT_GENERATOR")
        workflow.add_edge("INSIGHT_GENERATOR", "SCHEMA_ONTOLOGY")
        workflow.add_edge("SCHEMA_ONTOLOGY", "DATA_AUGMENTER")
        workflow.add_edge("DATA_AUGMENTER", "EMBEDDER")
        workflow.add_edge("EMBEDDER", "OUTPUT_FORMATTER")
        workflow.add_edge("OUTPUT_FORMATTER", END)
        
        # Compile the graph with MemorySaver
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    async def _input_node(self, state: SmartContractAnalysisState) -> SmartContractAnalysisState:
        """Initializes the state with contract data"""
        try:
            # Preprocess the source code
            source = state["source_code"]
            source = source.replace("\r", "").rstrip()
            source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
            source = re.sub(r'// SPDX-License-Identifier:.*\n', '', source)
            source = re.sub(r'\/\*[\s\S]*?\*\/|\/\/.*', '', source)
            
            # Apply token limit
            token_count = num_tokens_from_string(source, "cl100k_base")
            if token_count > 4000:
                source = source[:int(len(source) * (4000/token_count))]
            
            state["source_code"] = source
            return state
        except Exception as e:
            self.logger.error(f"Error in input node: {str(e)}")
            raise

    async def _info_extractor_node(self, state: SmartContractAnalysisState) -> SmartContractAnalysisState:
        """Extracts basic information from the contract"""
        try:
            # Extract basic contract information
            info_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a smart contract analyzer specialized in extracting structural information from Solidity code.
                Your task is to identify and extract key components like contract names, functions, events, state variables, and inheritance.
                Be precise and thorough in your extraction. Return only valid JSON with the specified fields."""),
                ("human", """
                Extract key information from this smart contract. Return JSON with:
                - contract_name: The name of the contract
                - functions: List of function names and their visibility
                - events: List of event names
                - state_variables: List of state variables and their types
                - inheritance: List of inherited contracts
                
                Contract code:
                {source_code}
                """)
            ])
            
            chain = info_prompt | self.llm | self.parser
            result = await chain.ainvoke({"source_code": state["source_code"]})
            
            state["extracted_infos"] = result
            return state
        except Exception as e:
            state["parsing_errors"] = [str(e)]
            self.logger.error(f"Error in info extractor: {str(e)}")
            return state

    async def _insight_generator_node(self, state: SmartContractAnalysisState) -> SmartContractAnalysisState:
        """Generates insights about the contract using LLM"""
        try:
            insight_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a smart contract security and functionality analyst.
                Your task is to analyze smart contracts and generate meaningful insights about their functionality, domain, security risks, and key features.
                Be thorough in identifying potential security risks and be specific about the contract's domain and functionality.
                Return only valid JSON with the specified fields."""),
                ("human", """
                Analyze this smart contract and its extracted information to generate insights. Return JSON with:
                - functionality: 2-3 sentence description of what the contract does
                - domain: DeFi, NFT, DAO, or Gaming
                - security_risks: list of potential security risks
                - key_features: list of notable features or patterns
                
                Contract code:
                {source_code}
                
                Extracted information:
                {extracted_infos}
                """)
            ])
            
            chain = insight_prompt | self.llm | self.parser
            result = await chain.ainvoke({
                "source_code": state["source_code"],
                "extracted_infos": state["extracted_infos"]
            })
            
            state["generated_insights"] = result
            return state
        except Exception as e:
            state["insight_generation_errors"] = [str(e)]
            self.logger.error(f"Error in insight generator: {str(e)}")
            return state

    async def _schema_ontology_node(self, state: SmartContractAnalysisState) -> SmartContractAnalysisState:
        """Populates the contract ontology"""
        try:
            ontology_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a smart contract ontology specialist.
                Your task is to analyze smart contracts and categorize them into a structured ontology that captures their type, access control mechanisms, state management, business logic, and external interactions.
                Be precise in identifying patterns and relationships. Return only valid JSON with the specified fields."""),
                ("human", """
                Based on the contract code and insights, populate the contract ontology. Return JSON with:
                - contract_type: The type of contract (e.g., Token, Marketplace, Governance)
                - access_control: List of access control mechanisms
                - state_management: How state is managed
                - business_logic: Key business logic patterns
                - external_interactions: List of external contract interactions
                
                Contract code:
                {source_code}
                
                Extracted information:
                {extracted_infos}
                
                Generated insights:
                {generated_insights}
                """)
            ])
            
            chain = ontology_prompt | self.llm | self.parser
            result = await chain.ainvoke({
                "source_code": state["source_code"],
                "extracted_infos": state["extracted_infos"],
                "generated_insights": state["generated_insights"]
            })
            
            state["populated_ontology"] = result
            return state
        except Exception as e:
            state["ontology_population_errors"] = [str(e)]
            self.logger.error(f"Error in schema ontology: {str(e)}")
            return state

    async def _data_augmenter_node(self, state: SmartContractAnalysisState) -> SmartContractAnalysisState:
        """Prepares data for embedding"""
        try:
            augmented_data = []
            
            # Create a rich text representation for embedding
            text = f"""
            Domain: {state['generated_insights']['domain']}
            Functionality: {state['generated_insights']['functionality']}
            Security Risks: {', '.join(state['generated_insights']['security_risks'])}
            Key Features: {', '.join(state['generated_insights']['key_features'])}
            Contract Type: {state['populated_ontology']['contract_type']}
            Access Control: {', '.join(state['populated_ontology']['access_control'])}
            Business Logic: {state['populated_ontology']['business_logic']}
            """
            
            augmented_data.append({
                "text": text,
                "metadata": {
                    "contract_id": state["contract_id"],
                    "domain": state["generated_insights"]["domain"],
                    "contract_type": state["populated_ontology"]["contract_type"]
                }
            })
            
            state["augmented_data_for_embedding"] = augmented_data
            return state
        except Exception as e:
            state["augmentation_errors"] = [str(e)]
            self.logger.error(f"Error in data augmenter: {str(e)}")
            return state

    async def _embedder_node(self, state: SmartContractAnalysisState) -> SmartContractAnalysisState:
        """Generates embeddings for the augmented data"""
        try:
            # Use the vector store's embedding model
            texts = [item["text"] for item in state["augmented_data_for_embedding"]]
            embeddings = self.vector_db.embedding_model.embed_documents(texts)
            
            state["embeddings"] = embeddings
            return state
        except Exception as e:
            state["embedding_errors"] = [str(e)]
            self.logger.error(f"Error in embedder: {str(e)}")
            return state

    async def _output_formatter_node(self, state: SmartContractAnalysisState) -> SmartContractAnalysisState:
        """Formats the final output for storage"""
        try:
            final_output = {
                "uid": state["contract_id"],
                "ContractDeployment.functionality": state["generated_insights"]["functionality"],
                "ContractDeployment.domain": state["generated_insights"]["domain"],
                "ContractDeployment.security_risks": state["generated_insights"]["security_risks"],
                "ContractDeployment.key_features": state["generated_insights"]["key_features"],
                "ContractDeployment.contract_type": state["populated_ontology"]["contract_type"],
                "ContractDeployment.access_control": state["populated_ontology"]["access_control"],
                "ContractDeployment.business_logic": state["populated_ontology"]["business_logic"]
            }
            
            state["final_processed_contract"] = final_output
            return state
        except Exception as e:
            self.logger.error(f"Error in output formatter: {str(e)}")
            raise

    async def enrich(self, contract_data: dict) -> dict:
        """
        Enriches a single contract using the agent workflow
        
        Args:
            contract_data: Dictionary containing contract information
            
        Returns:
            dict: Enriched contract data
        """
        try:
            # Initialize state
            initial_state = SmartContractAnalysisState(
                source_code=contract_data["ContractDeployment.verified_source_code"],
                contract_id=contract_data["uid"]
            )
            
            # Run the workflow with thread_id for state management
            config = {"configurable": {"thread_id": contract_data["uid"]}}
            final_state = await self.workflow.ainvoke(initial_state, config=config)
            
            # Store in vector database
            if final_state["augmented_data_for_embedding"]:
                self.vector_db.add_embeddings([final_state["final_processed_contract"]])
            
            return final_state["final_processed_contract"]
        except Exception as e:
            self.logger.error(f"Error during enrichment: {str(e)}")
            raise

class ParallelAgentEnricher:
    """Handles parallel processing of multiple contracts"""
    
    def __init__(self):
        self.enricher = AgentEnricher()

    async def process_contracts(self, contracts: List[dict]) -> List[dict]:
        """
        Process multiple contracts in parallel
        
        Args:
            contracts: List of contract dictionaries to process
            
        Returns:
            List[dict]: List of enriched contract data
        """
        tasks = []
        for contract in contracts:
            tasks.append(self.enricher.enrich(contract))
            self.logger.info(f"Enriching contract with UID: {contract['uid']}")
        return await asyncio.gather(*tasks)

if __name__ == "__main__":
    async def main():
        dgraph_client = DgraphClient()
        
        with open("./data/retrieved_enriched_contracts.json", "r") as file:
            contracts = json.load(file)["allContractDeployments"]
        
        parallel_enricher = ParallelAgentEnricher()
        
        logger.info("Starting parallel enrichment process...")
        response = await parallel_enricher.process_contracts(contracts)
        
        logger.info("Parallel enrichment process completed successfully")
        
        # Write the enriched data to a JSON file
        write_file(response, "parallel_enriched_data.json")
        
        # Store in Dgraph
        dgraph_client.mutate(response, commit_now=True)

    asyncio.run(main())
