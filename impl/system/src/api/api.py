from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn
from src.core.data_access.dgraph_client import DgraphClient
import yaml
import os


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
    functionalities: Optional[List[str]] = None
    standards: Optional[List[str]] = None
    patterns: Optional[List[str]] = None
    domain: Optional[str] = None
    security_risks: Optional[List[str]] = None
    similarity_score: Optional[float] = None  # For vector search results


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


# @app.post("/search")
# async def search_contracts(request: SearchRequest):
#     try:
#         results = retriever.search(request.query, request.limit)
#         formatted_results = []

#         if request.data:
#             client = DgraphClient()
#             for result in results:
#                 try:
#                     contract_data = client.get_contract_by_uid(
#                         result["metadata"]["dgraph_id"]
#                     )
#                     if not contract_data:
#                         continue

#                     contract = contract_data[0]

#                     formatted_result = ContractResult(
#                         id=contract.get("uid", ""),
#                         name=contract.get("ContractDeployment.name", ""),
#                         description=result.get("content", ""),
#                         created=contract.get("ContractDeployment.created", ""),
#                         verified=contract.get(
#                             "ContractDeployment.verified_source", False
#                         ),
#                         tags=[contract.get("ContractDeployment.domain", "")],
#                         storage_protocol=contract.get(
#                             "ContractDeployment.storage_protocol"
#                         ),
#                         storage_address=contract.get(
#                             "ContractDeployment.storage_address"
#                         ),
#                         experimental=contract.get("ContractDeployment.experimental"),
#                         solc_version=contract.get("ContractDeployment.solc_version"),
#                         verified_source=contract.get(
#                             "ContractDeployment.verified_source"
#                         ),
#                         verified_source_code=contract.get(
#                             "ContractDeployment.verified_source_code"
#                         ),
#                         functionality=contract.get("ContractDeployment.functionality"),
#                         domain=contract.get("ContractDeployment.domain"),
#                         security_risks=contract.get(
#                             "ContractDeployment.security_risks", []
#                         ),
#                     )
#                     print(formatted_result.id, formatted_result.description)
#                     formatted_results.append(formatted_result.model_dump())
#                 except Exception as e:
#                     print(f"Error processing contract: {str(e)}")
#                     continue
#             client.close()

#         return JSONResponse(content=formatted_results)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
client = DgraphClient()


@app.post("/search")
async def vector_search_contracts(request: VectorSearchRequest):
    """
    Perform vector similarity search on smart contracts using Dgraph's vector search.
    Converts natural language queries to embeddings and finds similar contracts.
    """
    try:
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
                    functionalities=result.get("ContractDeployment.functionalities"),
                    standards=result.get("ContractDeployment.standards"),
                    patterns=result.get("ContractDeployment.patterns"),
                    domain=result.get("ContractDeployment.application_domain"),
                    security_risks=result.get(
                        "ContractDeployment.security_risks_description", ""
                    ).split(", ")
                    if result.get("ContractDeployment.security_risks_description")
                    else [],
                    similarity_score=result.get("cosine_similarity"),
                )
                print(
                    f"Vector search result: {formatted_result.id}, {formatted_result.name}"
                )
                formatted_results.append(formatted_result.model_dump())
            except Exception as e:
                print(f"Error processing vector search result: {str(e)}")
                print(f"Result data: {result['ContractDeployment.id']}")
                continue

        return JSONResponse(content=formatted_results)
    except Exception as e:
        print(f"Vector search error: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search_text_source_code")
async def search_text_source_code_contracts(request: SearchRequest):
    """
    Perform text search on smart contracts focusing on name and source code.
    Uses literal string matching for more precise results.
    """
    try:
        results = client.search_by_text_source_code(request.query, request.limit)
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
                    functionalities=result.get("ContractDeployment.functionalities"),
                    standards=result.get("ContractDeployment.standards"),
                    patterns=result.get("ContractDeployment.patterns"),
                    domain=result.get("ContractDeployment.application_domain"),
                    security_risks=result.get(
                        "ContractDeployment.security_risks_description", ""
                    ).split(", ")
                    if result.get("ContractDeployment.security_risks_description")
                    else [],
                )
                print(
                    f"Text source code search result: {formatted_result.id}, {formatted_result.name}"
                )
                formatted_results.append(formatted_result.model_dump())
            except Exception as e:
                print(f"Error processing text source code search result: {str(e)}")
                continue

        return JSONResponse(content=formatted_results)
    except Exception as e:
        print(f"Text source code search error: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search_text")
async def search_text_contracts(request: SearchRequest):
    """
    Perform comprehensive text search on smart contracts across all metadata fields.
    Uses literal string matching for finding contracts by various criteria.
    """
    try:
        results = client.search_by_text(request.query, request.limit)
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
                    functionalities=result.get("ContractDeployment.functionalities"),
                    standards=result.get("ContractDeployment.standards"),
                    patterns=result.get("ContractDeployment.patterns"),
                    domain=result.get("ContractDeployment.application_domain"),
                    security_risks=result.get(
                        "ContractDeployment.security_risks_description", ""
                    ).split(", ")
                    if result.get("ContractDeployment.security_risks_description")
                    else [],
                )
                print(
                    f"Text search result: {formatted_result.id}, {formatted_result.name}"
                )
                formatted_results.append(formatted_result.model_dump())
            except Exception as e:
                print(f"Error processing text search result: {str(e)}")
                continue

        return JSONResponse(content=formatted_results)
    except Exception as e:
        print(f"Text search error: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
                    
                    <p style="margin-top: 16px; margin-bottom: 0; color: #666; font-size: 14px;">
                        💡 <strong>Tip:</strong> Check the Swagger UI above to test both endpoints interactively.
                    </p>
                </div>
            </div>
        </body>
    </html>
    """


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",  # Allows external access
        port=8000,  # Default port
    )
