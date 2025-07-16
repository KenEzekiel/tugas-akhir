from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from src.core.data_retrieval.lightweight_retriever import LightweightRetriever
import uvicorn
from src.core.data_access.dgraph_client import DgraphClient
import json
import yaml
import os
from openai import OpenAI


# Load custom OpenAPI spec
def load_openapi_spec():
    try:
        spec_path = os.path.join(os.path.dirname(__file__), "..", "..", "openapi.yaml")
        with open(spec_path, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Warning: Could not load custom OpenAPI spec: {e}")
        return None


app = FastAPI()

# Load and set custom OpenAPI spec
custom_openapi = load_openapi_spec()
if custom_openapi:

    def custom_openapi_func():
        return custom_openapi

    app.openapi = custom_openapi_func

retriever = LightweightRetriever()

# Initialize OpenAI client
openai_client = None
try:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
        print("OpenAI client initialized successfully")
    else:
        print("Warning: OPENAI_API_KEY not found in environment variables")
except Exception as e:
    print(f"Warning: Failed to initialize OpenAI client: {e}")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
)


class SearchRequest(BaseModel):
    query: str
    limit: int
    data: bool = False


class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of results")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")


class ContractResult(BaseModel):
    id: str
    name: str
    symbol: str = ""  # Default empty as it might not always be present
    description: str
    license: str = "UNLICENSED"  # Default value
    created: str
    verified: bool
    tags: List[str]
    externalUrl: Optional[str] = None
    address: Optional[str] = None
    storage_protocol: Optional[str] = None
    storage_address: Optional[str] = None
    experimental: Optional[bool] = None
    solc_version: Optional[str] = None
    verified_source: Optional[bool] = None
    verified_source_code: Optional[str] = None
    functionality: Optional[str] = None
    domain: Optional[str] = None
    security_risks: Optional[List[str]] = None
    similarity_score: Optional[float] = None  # For vector search results


class Config:
    json_encoders = {
        # Add custom JSON encoders if needed
    }


# class SearchRequest(BaseModel):
#     query: str = Field(..., min_length=1, description="Search query string")
#     limit: int = Field(..., ge=1, le=100, description="Maximum number of results")
#     data: bool = Field(
#         False, description="Include comprehensive contract data and analysis"
#     )


# class Account(BaseModel):
#     uid: Optional[str] = None
#     address: Optional[str] = None
#     tags: Optional[List[str]] = None
#     is_contract: Optional[bool] = None


# class Block(BaseModel):
#     uid: Optional[str] = None
#     number: Optional[int] = None
#     datetime: Optional[str] = None
#     difficulty: Optional[str] = None
#     size: Optional[int] = None


# class ContractParam(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     data_type: Optional[str] = None
#     storage_location: Optional[str] = None
#     is_indexed: Optional[bool] = None


# class StateVariable(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     data_type: Optional[str] = None
#     visibility: Optional[str] = None
#     immutability: Optional[str] = None
#     natspec_dev: Optional[str] = None


# class FunctionDef(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     visibility: Optional[str] = None
#     mutability: Optional[str] = None
#     modifiers_used: Optional[List[str]] = None
#     natspec_dev: Optional[str] = None
#     natspec_notice: Optional[str] = None
#     internal_function_calls: Optional[List[str]] = None
#     external_call_signatures: Optional[List[str]] = None
#     emitted_events: Optional[List[str]] = None
#     reads_state_variables: Optional[List[str]] = None
#     writes_state_variables: Optional[List[str]] = None
#     parameters: Optional[List[ContractParam]] = None
#     returns: Optional[List[ContractParam]] = None


# class EventDef(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     natspec_dev: Optional[str] = None
#     natspec_notice: Optional[str] = None
#     parameters: Optional[List[ContractParam]] = None


# class ModifierDef(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     parameters: Optional[List[ContractParam]] = None


# class StructMember(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     data_type: Optional[str] = None


# class StructDef(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     members: Optional[List[StructMember]] = None


# class EnumDef(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     values: Optional[List[str]] = None


# class CustomErrorDef(BaseModel):
#     uid: Optional[str] = None
#     name: Optional[str] = None
#     parameters: Optional[List[ContractParam]] = None


# class ParsedContractData(BaseModel):
#     uid: Optional[str] = None
#     source_contract_name: Optional[str] = None
#     imports: Optional[List[str]] = None
#     inherits_from: Optional[List[str]] = None
#     implemented_interfaces_source: Optional[List[str]] = None
#     natspec_contract_dev: Optional[str] = None
#     natspec_contract_notice: Optional[str] = None
#     token_name_literal: Optional[str] = None
#     token_symbol_literal: Optional[str] = None
#     state_variables: Optional[List[StateVariable]] = None
#     functions: Optional[List[FunctionDef]] = None
#     events: Optional[List[EventDef]] = None
#     modifiers: Optional[List[ModifierDef]] = None
#     structs: Optional[List[StructDef]] = None
#     enums: Optional[List[EnumDef]] = None
#     custom_errors: Optional[List[CustomErrorDef]] = None


# class FunctionPurpose(BaseModel):
#     uid: Optional[str] = None
#     function_name: Optional[str] = None
#     purpose_description: Optional[str] = None


# class InferredRole(BaseModel):
#     uid: Optional[str] = None
#     role_name: Optional[str] = None
#     description: Optional[str] = None
#     associated_functions: Optional[List[str]] = None


# class SecurityRiskHint(BaseModel):
#     uid: Optional[str] = None
#     risk_type: Optional[str] = None
#     description: Optional[str] = None
#     affected_elements: Optional[List[str]] = None
#     severity: Optional[str] = None


# class FunctionSummary(BaseModel):
#     uid: Optional[str] = None
#     function_name: Optional[str] = None
#     plain_english_summary: Optional[str] = None


# class ContractAnalysis(BaseModel):
#     uid: Optional[str] = None
#     contract_purpose: Optional[List[str]] = None
#     access_control_patterns: Optional[List[str]] = None
#     state_management_patterns: Optional[List[str]] = None
#     design_patterns: Optional[List[str]] = None
#     financial_operations_detected: Optional[List[str]] = None
#     tokenomics_hints: Optional[List[str]] = None
#     standard_adherence: Optional[List[str]] = None
#     high_level_summary: Optional[str] = None
#     function_purposes: Optional[List[FunctionPurpose]] = None
#     inferred_roles: Optional[List[InferredRole]] = None
#     security_risks_detected: Optional[List[SecurityRiskHint]] = None
#     function_summaries: Optional[List[FunctionSummary]] = None


# class ContractDeploymentResult(BaseModel):
#     uid: str
#     name: str
#     description: str
#     verified_source: bool

#     # Optional contract deployment fields
#     functionality: Optional[str] = None
#     domain: Optional[str] = None
#     security_risks: Optional[List[str]] = None
#     tx_hash: Optional[str] = None
#     failed_deploy: Optional[bool] = None
#     creation_bytecode: Optional[str] = None
#     deployed_bytecode: Optional[str] = None
#     storage_protocol: Optional[str] = None
#     storage_address: Optional[str] = None
#     experimental: Optional[bool] = None
#     solc_version: Optional[str] = None
#     verified_source_code: Optional[str] = None

#     # Related entities (populated when data=True)
#     creator: Optional[Account] = None
#     block: Optional[Block] = None
#     parsed_source_data: Optional[ParsedContractData] = None
#     analysis: Optional[ContractAnalysis] = None


class RefineRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Original search query to refine")


class RefineResponse(BaseModel):
    original_query: str = Field(..., description="The original query provided")
    refined_query: str = Field(..., description="The enhanced, more descriptive query")
    reasoning: Optional[str] = Field(None, description="Explanation of the refinement")


def parse_dgraph_entity(data: dict, entity_type: str) -> dict:
    """Parse a Dgraph entity and return a clean dict"""
    if not data:
        return {}

    result = {}
    for key, value in data.items():
        # Remove type prefix from keys
        clean_key = key.replace(f"{entity_type}.", "")
        result[clean_key] = value

    return result


def extract_related_entities(contract_data: dict, data_requested: bool) -> dict:
    """Extract and parse related entities from contract data"""
    related = {}

    if not data_requested:
        return related

    # Extract creator (Account)
    if "ContractDeployment.creator" in contract_data:
        creator_data = contract_data["ContractDeployment.creator"]
        if isinstance(creator_data, list) and creator_data:
            creator_info = parse_dgraph_entity(creator_data[0], "Account")
            related["creator"] = Account(**creator_info)

    # Extract block
    if "ContractDeployment.block" in contract_data:
        block_data = contract_data["ContractDeployment.block"]
        if isinstance(block_data, list) and block_data:
            block_info = parse_dgraph_entity(block_data[0], "Block")
            related["block"] = Block(**block_info)

    # Extract parsed source data
    if "ContractDeployment.parsed_source_data" in contract_data:
        parsed_data = contract_data["ContractDeployment.parsed_source_data"]
        if isinstance(parsed_data, list) and parsed_data:
            parsed_info = parse_dgraph_entity(parsed_data[0], "ParsedContractData")

            # Extract nested entities within parsed data
            for nested_key in [
                "state_variables",
                "functions",
                "events",
                "modifiers",
                "structs",
                "enums",
                "custom_errors",
            ]:
                if f"ParsedContractData.{nested_key}" in parsed_data[0]:
                    nested_data = parsed_data[0][f"ParsedContractData.{nested_key}"]
                    parsed_info[nested_key] = parse_nested_entities(
                        nested_data, nested_key
                    )

            related["parsed_source_data"] = ParsedContractData(**parsed_info)

    # Extract analysis
    if "ContractDeployment.analysis" in contract_data:
        analysis_data = contract_data["ContractDeployment.analysis"]
        if isinstance(analysis_data, list) and analysis_data:
            analysis_info = parse_dgraph_entity(analysis_data[0], "ContractAnalysis")

            # Extract nested analysis entities
            for nested_key in [
                "function_purposes",
                "inferred_roles",
                "security_risks_detected",
                "function_summaries",
            ]:
                if f"ContractAnalysis.{nested_key}" in analysis_data[0]:
                    nested_data = analysis_data[0][f"ContractAnalysis.{nested_key}"]
                    analysis_info[nested_key] = parse_nested_entities(
                        nested_data, nested_key
                    )

            related["analysis"] = ContractAnalysis(**analysis_info)

    return related


def parse_nested_entities(nested_data: List[dict], entity_type: str) -> List[dict]:
    """Parse nested entities like functions, state variables, etc."""
    if not nested_data:
        return []

    result = []
    for item in nested_data:
        if isinstance(item, dict):
            # Map entity types to their models
            type_mapping = {
                "state_variables": ("StateVariable", StateVariable),
                "functions": ("FunctionDef", FunctionDef),
                "events": ("EventDef", EventDef),
                "modifiers": ("ModifierDef", ModifierDef),
                "structs": ("StructDef", StructDef),
                "enums": ("EnumDef", EnumDef),
                "custom_errors": ("CustomErrorDef", CustomErrorDef),
                "function_purposes": ("FunctionPurpose", FunctionPurpose),
                "inferred_roles": ("InferredRole", InferredRole),
                "security_risks_detected": ("SecurityRiskHint", SecurityRiskHint),
                "function_summaries": ("FunctionSummary", FunctionSummary),
            }

            if entity_type in type_mapping:
                prefix, model_class = type_mapping[entity_type]
                parsed_item = parse_dgraph_entity(item, prefix)

                # Handle nested parameters for functions, events, etc.
                if "parameters" in parsed_item and isinstance(
                    parsed_item["parameters"], list
                ):
                    parsed_item["parameters"] = [
                        ContractParam(**parse_dgraph_entity(param, "ContractParam"))
                        for param in parsed_item["parameters"]
                        if isinstance(param, dict)
                    ]

                result.append(model_class(**parsed_item))

    return result


# @app.post("/search")
# async def search_contracts(request: SearchRequest):
#     try:
#         # Get search results from retriever
#         results = retriever.search(request.query, request.limit)
#         formatted_results = []

#         if request.data:
#             # Use Dgraph client for detailed data
#             client = DgraphClient()
#             for result in results:
#                 try:
#                     # Get comprehensive contract data
#                     contract_data = client.get_contract_by_uid(
#                         result["metadata"]["dgraph_id"]
#                     )
#                     print(contract_data)
#                     if (
#                         not contract_data
#                         or "contract" not in contract_data
#                         or not contract_data["contract"]
#                     ):
#                         continue

#                     contract = contract_data[0]

#                     # Parse main contract deployment data
#                     main_data = parse_dgraph_entity(contract, "ContractDeployment")

#                     # Add basic required fields
#                     main_data.update(
#                         {
#                             "uid": contract["uid"],
#                             "name": contract.get("ContractDeployment.name", ""),
#                             "description": result.get("content", ""),
#                             "verified_source": contract.get(
#                                 "ContractDeployment.verified_source", False
#                             ),
#                         }
#                     )

#                     print(main_data)

#                     # Extract related entities if data is requested
#                     related_entities = extract_related_entities(contract, request.data)
#                     main_data.update(related_entities)

#                     # Create the result object
#                     formatted_result = ContractDeploymentResult(**main_data)
#                     formatted_results.append(formatted_result.model_dump())

#                 except Exception as e:
#                     print(f"Error processing contract: {str(e)}")
#                     continue

#             client.close()
#         else:
#             # Return basic results without detailed data
#             for result in results:
#                 try:
#                     basic_result = ContractDeploymentResult(
#                         uid=result["metadata"].get("dgraph_id", ""),
#                         name=result["metadata"].get("title", "Unknown"),
#                         description=result.get("content", ""),
#                         verified_source=True,  # Assume verified if in search results
#                     )
#                     formatted_results.append(basic_result.model_dump())
#                 except Exception as e:
#                     print(f"Error processing basic result: {str(e)}")
#                     continue

#         return JSONResponse(content=formatted_results)

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_contracts(request: SearchRequest):
    try:
        results = retriever.search(request.query, request.limit)
        formatted_results = []

        if request.data:
            client = DgraphClient()
            for result in results:
                try:
                    contract_data = client.get_contract_by_uid(
                        result["metadata"]["dgraph_id"]
                    )
                    if not contract_data:
                        continue

                    contract = contract_data[0]

                    formatted_result = ContractResult(
                        id=contract.get("uid", ""),
                        name=contract.get("ContractDeployment.name", ""),
                        description=result.get("content", ""),
                        created=contract.get("ContractDeployment.created", ""),
                        verified=contract.get(
                            "ContractDeployment.verified_source", False
                        ),
                        tags=[contract.get("ContractDeployment.domain", "")],
                        storage_protocol=contract.get(
                            "ContractDeployment.storage_protocol"
                        ),
                        storage_address=contract.get(
                            "ContractDeployment.storage_address"
                        ),
                        experimental=contract.get("ContractDeployment.experimental"),
                        solc_version=contract.get("ContractDeployment.solc_version"),
                        verified_source=contract.get(
                            "ContractDeployment.verified_source"
                        ),
                        verified_source_code=contract.get(
                            "ContractDeployment.verified_source_code"
                        ),
                        functionality=contract.get("ContractDeployment.functionality"),
                        domain=contract.get("ContractDeployment.domain"),
                        security_risks=contract.get(
                            "ContractDeployment.security_risks", []
                        ),
                    )
                    print(formatted_result.id, formatted_result.description)
                    formatted_results.append(formatted_result.model_dump())
                except Exception as e:
                    print(f"Error processing contract: {str(e)}")
                    continue
            client.close()

        return JSONResponse(content=formatted_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vector_search")
async def vector_search_contracts(request: VectorSearchRequest):
    """
    Perform vector similarity search on smart contracts using Dgraph's vector search.
    Converts natural language queries to embeddings and finds similar contracts.
    """
    try:
        client = DgraphClient()
        results = client.vector_search(request.query, request.limit)
        formatted_results = []

        for result in results:
            try:
                formatted_result = ContractResult(
                    id=result.get("uid", ""),
                    name=result.get("ContractDeployment.name", ""),
                    description=result.get("ContractDeployment.description", ""),
                    created=result.get("ContractDeployment.created", ""),
                    verified=result.get("ContractDeployment.verified_source", False),
                    tags=[result.get("ContractDeployment.application_domain", "")],
                    storage_protocol=result.get("ContractDeployment.storage_protocol"),
                    storage_address=result.get("ContractDeployment.storage_address"),
                    experimental=result.get("ContractDeployment.experimental"),
                    solc_version=result.get("ContractDeployment.solc_version"),
                    verified_source=result.get("ContractDeployment.verified_source"),
                    verified_source_code=result.get(
                        "ContractDeployment.verified_source_code"
                    ),
                    functionality=result.get(
                        "ContractDeployment.functionality_classification"
                    ),
                    domain=result.get("ContractDeployment.application_domain"),
                    security_risks=result.get(
                        "ContractDeployment.security_risks_description", ""
                    ).split(", ")
                    if result.get("ContractDeployment.security_risks_description")
                    else [],
                )
                print(
                    f"Vector search result: {formatted_result.id}, {formatted_result.name}"
                )
                formatted_results.append(formatted_result.model_dump())
            except Exception as e:
                print(f"Error processing vector search result: {str(e)}")
                print(f"Result data: {result}")
                continue

        client.close()
        return JSONResponse(content=formatted_results)
    except Exception as e:
        print(f"Vector search error: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/refine", response_model=RefineResponse)
async def refine_query(request: RefineRequest):
    """
    Refine and enhance a search query using AI to make it more semantically rich
    for better smart contract search results.
    """
    try:
        print(f"Refining query: {request.query}")

        # Use LLM to refine the query
        refined_response = await refine_query_with_llm(request.query)

        print(f"Refined query: {refined_response.refined_query}")

        return refined_response

    except Exception as e:
        print(f"Error refining query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refine query: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """API Documentation Landing Page"""
    return """
    <html>
        <head>
            <title>Smart Contract Search API</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    margin: 0; 
                    padding: 40px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #333;
                }
                .container { 
                    max-width: 800px; 
                    margin: 0 auto; 
                    background: white;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                }
                .header {
                    text-align: center;
                    margin-bottom: 40px;
                }
                .logo {
                    font-size: 48px;
                    margin-bottom: 16px;
                }
                h1 { 
                    color: #2c3e50; 
                    margin: 0 0 16px 0;
                    font-size: 32px;
                    font-weight: 700;
                }
                .subtitle {
                    color: #666;
                    font-size: 18px;
                    margin-bottom: 40px;
                }
                .link-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }
                .link-card { 
                    display: block; 
                    padding: 24px; 
                    border: 2px solid #e1e8ed; 
                    border-radius: 12px; 
                    text-decoration: none; 
                    color: #333;
                    transition: all 0.3s ease;
                    background: #fff;
                }
                .link-card:hover { 
                    border-color: #667eea;
                    transform: translateY(-4px);
                    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.15);
                }
                .card-icon {
                    font-size: 32px;
                    margin-bottom: 12px;
                    display: block;
                }
                .card-title { 
                    color: #2c3e50; 
                    margin: 0 0 8px 0; 
                    font-size: 20px;
                    font-weight: 600;
                }
                .card-desc { 
                    margin: 0; 
                    color: #666; 
                    font-size: 14px;
                    line-height: 1.5;
                }
                .api-info {
                    background: #f8f9fa;
                    padding: 24px;
                    border-radius: 12px;
                    border-left: 4px solid #667eea;
                }
                .endpoint {
                    background: #fff;
                    padding: 16px;
                    border-radius: 8px;
                    border: 1px solid #e1e8ed;
                    margin-top: 16px;
                    font-family: 'Monaco', 'Menlo', monospace;
                }
                .method {
                    background: #28a745;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-right: 12px;
                }
                .url {
                    color: #495057;
                }
                @media (max-width: 768px) {
                    body { padding: 20px; }
                    .container { padding: 24px; }
                    h1 { font-size: 28px; }
                    .link-grid { grid-template-columns: 1fr; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🔍</div>
                    <h1>Smart Contract Search API</h1>
                    <p class="subtitle">Discover and explore smart contracts with AI-powered search</p>
                </div>
                
                <div class="link-grid">
                    <a href="/docs" class="link-card">
                        <span class="card-icon">📚</span>
                        <h2 class="card-title">Swagger UI</h2>
                        <p class="card-desc">Interactive API documentation with live testing capabilities</p>
                    </a>
                    
                    <a href="/redoc" class="link-card">
                        <span class="card-icon">📖</span>
                        <h2 class="card-title">ReDoc</h2>
                        <p class="card-desc">Clean, responsive API documentation with detailed schemas</p>
                    </a>
                    
                    <a href="/openapi.json" class="link-card">
                        <span class="card-icon">📄</span>
                        <h2 class="card-title">OpenAPI Spec</h2>
                        <p class="card-desc">Raw OpenAPI specification in JSON format for integrations</p>
                    </a>
                </div>
                
                <div class="api-info">
                    <h3 style="margin-top: 0; color: #2c3e50;">🚀 Quick Start</h3>
                    <p style="margin-bottom: 16px; color: #666;">Ready to search for smart contracts? Use our search endpoint:</p>
                    
                    <div class="endpoint">
                        <span class="method">POST</span>
                        <span class="url">/search</span>
                    </div>
                    
                    <div class="endpoint">
                        <span class="method">POST</span>
                        <span class="url">/vector_search</span>
                    </div>
                    
                    <p style="margin-top: 16px; margin-bottom: 0; color: #666; font-size: 14px;">
                        💡 <strong>Tip:</strong> Check the Swagger UI above to test both endpoints interactively.
                    </p>
                </div>
            </div>
        </body>
    </html>
    """


# ========================================================================
# Query Refinement System
# ========================================================================

QUERY_REFINEMENT_SYSTEM_PROMPT = """You are an expert smart contract search query enhancement assistant. Your role is to transform user queries into more detailed, semantically rich descriptions that will improve search results for smart contracts.

TASK: Take a user's search query and enhance it with:
1. Technical terminology relevant to blockchain/smart contracts
2. Specific functionality descriptions
3. Common patterns and standards (ERC20, ERC721, DeFi protocols, etc.)
4. Security considerations when relevant
5. Use cases and business logic details

GUIDELINES:
- Keep the core intent of the original query
- Add semantic depth without changing the meaning
- Include relevant technical terms that developers would use
- Mention specific standards, patterns, or protocols when applicable
- Be concise but descriptive (aim for 1-3 sentences)
- Focus on functionality, not implementation details

EXAMPLES:
Input: "token contract"
Output: "ERC20 or ERC721 token contract implementations with standard transfer functionality, allowance mechanisms, and potentially mintable or burnable capabilities"

Input: "NFT marketplace"
Output: "Non-fungible token marketplace smart contracts implementing ERC721 or ERC1155 standards with auction mechanisms, royalty distribution, and decentralized trading functionality"

Input: "lending protocol"
Output: "Decentralized finance lending and borrowing protocols with collateral management, interest rate calculations, liquidation mechanisms, and automated market maker integration"

Return your response as a JSON object with:
- "refined_query": the enhanced query
- "reasoning": brief explanation of what you added and why

Be helpful and precise. Transform the query to maximize smart contract search relevance."""


async def refine_query_with_llm(original_query: str) -> RefineResponse:
    """Use OpenAI to refine and enhance the search query"""

    if not openai_client:
        # Fallback: return original query with a note
        return RefineResponse(
            original_query=original_query,
            refined_query=original_query,
            reasoning="LLM service not available - using original query",
        )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using the more cost-effective model
            messages=[
                {"role": "system", "content": QUERY_REFINEMENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Please refine this search query: {original_query}",
                },
            ],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        return RefineResponse(
            original_query=original_query,
            refined_query=result.get("refined_query", original_query),
            reasoning=result.get("reasoning", "Query enhanced with semantic details"),
        )

    except Exception as e:
        print(f"Error refining query with LLM: {str(e)}")
        # Fallback to rule-based enhancement
        return fallback_query_enhancement(original_query)


def fallback_query_enhancement(original_query: str) -> RefineResponse:
    """Fallback query enhancement using rule-based patterns"""

    query_lower = original_query.lower()
    enhancements = []

    # Token-related enhancements
    if any(word in query_lower for word in ["token", "coin", "currency"]):
        enhancements.append("ERC20 or ERC721 token standard implementation")

    # NFT-related enhancements
    if any(word in query_lower for word in ["nft", "collectible", "art", "gaming"]):
        enhancements.append(
            "non-fungible token with metadata and ownership transfer capabilities"
        )

    # DeFi-related enhancements
    if any(
        word in query_lower for word in ["defi", "lending", "borrowing", "liquidity"]
    ):
        enhancements.append(
            "decentralized finance protocol with automated market maker functionality"
        )

    # Governance enhancements
    if any(word in query_lower for word in ["governance", "voting", "dao"]):
        enhancements.append(
            "decentralized governance system with proposal and voting mechanisms"
        )

    # Security enhancements
    if any(word in query_lower for word in ["security", "audit", "safe"]):
        enhancements.append(
            "security-focused implementation with access controls and vulnerability mitigations"
        )

    if enhancements:
        refined = f"{original_query} - {', '.join(enhancements)}"
        reasoning = (
            "Enhanced with rule-based pattern matching for blockchain terminology"
        )
    else:
        refined = f"{original_query} smart contract functionality with standard implementation patterns"
        reasoning = "Added general smart contract context"

    return RefineResponse(
        original_query=original_query, refined_query=refined, reasoning=reasoning
    )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",  # Allows external access
        port=8000,  # Default port
    )
