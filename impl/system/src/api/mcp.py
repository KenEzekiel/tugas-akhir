import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.core.data_access.vectordb_client import VectorDBManager
from src.core.data_access.dgraph_client import DgraphClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol Version
MCP_VERSION = "2025-03-26"


class ErrorCode(Enum):
    # Standard JSON-RPC error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific error codes
    INVALID_VERSION = -32000
    INITIALIZATION_FAILED = -32001
    TOOL_EXECUTION_ERROR = -32002
    RESOURCE_NOT_FOUND = -32003


@dataclass
class MCPError:
    code: int
    message: str
    data: Optional[Any] = None


@dataclass
class JSONRPCRequest:
    jsonrpc: str
    method: str
    id: Optional[Union[str, int]] = None
    params: Optional[Dict[str, Any]] = None


@dataclass
class JSONRPCResponse:
    jsonrpc: str
    id: Optional[Union[str, int]]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class Tool:
    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class Resource:
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


@dataclass
class Prompt:
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class MCPServer:
    def __init__(self):
        self.vector_db = VectorDBManager("config/vectordb.yaml")
        self.initialized = False
        self.client_info = None

        # Define available tools
        self.tools = [
            Tool(
                name="search_contracts",
                description="Search for smart contracts using semantic search",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for finding relevant contracts",
                        },
                        "k": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="vector_search_contracts",
                description="Search for smart contracts using vector similarity search with natural language queries",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query for finding similar contracts",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                        "threshold": {
                            "type": "number",
                            "description": "Similarity threshold (0.0 to 1.0)",
                            "default": 0.7,
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_contract_details",
                description="Get detailed information about a specific contract by UID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "uid": {
                            "type": "string",
                            "description": "Unique identifier of the contract",
                        }
                    },
                    "required": ["uid"],
                },
            ),
        ]

        # Define available resources
        self.resources = [
            Resource(
                uri="contracts://all",
                name="All Contracts",
                description="Access to all smart contracts in the database",
                mimeType="application/json",
            ),
            Resource(
                uri="contracts://search",
                name="Contract Search",
                description="Semantic search interface for smart contracts",
                mimeType="application/json",
            ),
        ]

        # Define available prompts
        self.prompts = [
            Prompt(
                name="analyze_contract",
                description="Analyze a smart contract for security vulnerabilities and patterns",
                arguments=[
                    {
                        "name": "contract_address",
                        "description": "The contract address to analyze",
                        "required": True,
                    },
                    {
                        "name": "analysis_type",
                        "description": "Type of analysis: security, patterns, or full",
                        "required": False,
                    },
                ],
            ),
            Prompt(
                name="compare_contracts",
                description="Compare multiple contracts for similarities and differences",
                arguments=[
                    {
                        "name": "contract_uids",
                        "description": "List of contract UIDs to compare",
                        "required": True,
                    }
                ],
            ),
        ]

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        protocol_version = params.get("protocolVersion")
        if protocol_version != MCP_VERSION:
            raise MCPError(
                ErrorCode.INVALID_VERSION.value,
                f"Unsupported protocol version: {protocol_version}. Expected: {MCP_VERSION}",
            )

        client_info = params.get("clientInfo", {})
        self.client_info = client_info

        logger.info(f"Initializing MCP server for client: {client_info}")

        return {
            "protocolVersion": MCP_VERSION,
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True},
                "logging": {},
            },
            "serverInfo": {
                "name": "Smart Contract Discovery MCP Server",
                "version": "1.0.0",
                "description": "MCP server for searching and analyzing smart contracts",
            },
        }

    def handle_initialized(self, params: Optional[Dict[str, Any]] = None) -> None:
        """Handle MCP initialized notification"""
        self.initialized = True
        logger.info("MCP server initialized successfully")

    def handle_tools_list(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {"tools": [asdict(tool) for tool in self.tools]}

    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "search_contracts":
                return self._search_contracts(arguments)
            elif tool_name == "vector_search_contracts":
                return self._vector_search_contracts(arguments)
            elif tool_name == "get_contract_details":
                return self._get_contract_details(arguments)
            else:
                raise MCPError(
                    ErrorCode.METHOD_NOT_FOUND.value, f"Unknown tool: {tool_name}"
                )
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            raise MCPError(
                ErrorCode.TOOL_EXECUTION_ERROR.value, f"Tool execution failed: {str(e)}"
            )

    def handle_resources_list(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle resources/list request"""
        return {"resources": [asdict(resource) for resource in self.resources]}

    def handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")

        if uri == "contracts://all":
            return self._get_all_contracts()
        elif uri == "contracts://search":
            return self._get_search_interface()
        else:
            raise MCPError(
                ErrorCode.RESOURCE_NOT_FOUND.value, f"Resource not found: {uri}"
            )

    def handle_prompts_list(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle prompts/list request"""
        return {"prompts": [asdict(prompt) for prompt in self.prompts]}

    def handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        if prompt_name == "analyze_contract":
            return self._get_analyze_contract_prompt(arguments)
        elif prompt_name == "compare_contracts":
            return self._get_compare_contracts_prompt(arguments)
        else:
            raise MCPError(
                ErrorCode.METHOD_NOT_FOUND.value, f"Unknown prompt: {prompt_name}"
            )

    def _search_contracts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute contract search tool"""
        query = arguments.get("query")
        k = arguments.get("k", 5)

        if not query:
            raise ValueError("Query parameter is required")

        results = self.vector_db.search(query, k=k)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {len(results)} contracts matching '{query}':\n\n"
                    + "\n".join(
                        [
                            f"Contract {i + 1}:\n"
                            f"Content: {r['content'][:200]}...\n"
                            f"Metadata: {json.dumps(r['metadata'], indent=2)}\n"
                            for i, r in enumerate(results)
                        ]
                    ),
                }
            ]
        }

    def _vector_search_contracts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute vector similarity search tool"""
        query = arguments.get("query")
        limit = arguments.get("limit", 5)

        if not query:
            raise ValueError("Query parameter is required")

        client = DgraphClient()
        try:
            results = client.vector_search(query, limit=limit)

            formatted_results = []
            for i, result in enumerate(results):
                formatted_results.append(
                    f"Contract {i + 1}:\n"
                    f"UID: {result.get('uid', 'N/A')}\n"
                    f"Name: {result.get('ContractDeployment.name', 'N/A')}\n"
                    f"Description: {result.get('ContractDeployment.description', 'N/A')[:200]}...\n"
                    f"Domain: {result.get('ContractDeployment.application_domain', 'N/A')}\n"
                    f"Functionality: {result.get('ContractDeployment.functionality_classification', 'N/A')}\n"
                    f"Verified: {result.get('ContractDeployment.verified_source', False)}\n"
                )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Found {len(results)} contracts similar to '{query}' (threshold: {threshold}):\n\n"
                        + "\n".join(formatted_results)
                        if formatted_results
                        else "No similar contracts found.",
                    }
                ]
            }
        finally:
            client.close()

    def _get_contract_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get contract details by UID"""
        uid = arguments.get("uid")

        if not uid:
            raise ValueError("UID parameter is required")

        client = DgraphClient()
        try:
            result = client.get_contract_by_uid(uid)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Contract Details for UID {uid}:\n\n{json.dumps(result, indent=2)}",
                    }
                ]
            }
        finally:
            client.close()

    def _get_all_contracts(self) -> Dict[str, Any]:
        """Get all contracts resource"""
        return {
            "contents": [
                {
                    "uri": "contracts://all",
                    "mimeType": "application/json",
                    "text": json.dumps(
                        {
                            "description": "Access to all smart contracts in the database",
                            "endpoint": "/search",
                            "capabilities": ["search", "get_details"],
                        },
                        indent=2,
                    ),
                }
            ]
        }

    def _get_search_interface(self) -> Dict[str, Any]:
        """Get search interface resource"""
        return {
            "contents": [
                {
                    "uri": "contracts://search",
                    "mimeType": "application/json",
                    "text": json.dumps(
                        {
                            "description": "Semantic search interface for smart contracts",
                            "parameters": {
                                "query": "Search query string",
                                "k": "Number of results (1-20, default 5)",
                            },
                            "example": {"query": "ERC20 token contract", "k": 5},
                        },
                        indent=2,
                    ),
                }
            ]
        }

    def _get_analyze_contract_prompt(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get contract analysis prompt"""
        contract_address = arguments.get("contract_address", "[CONTRACT_ADDRESS]")
        analysis_type = arguments.get("analysis_type", "full")

        prompt_text = f"""You are a smart contract security expert. Please analyze the contract at address {contract_address}.

Perform a {analysis_type} analysis and provide insights on:

1. **Security Vulnerabilities**: Look for common issues like reentrancy, overflow/underflow, access control problems
2. **Code Patterns**: Identify design patterns used (proxy, factory, etc.)
3. **Gas Optimization**: Suggest improvements for gas efficiency  
4. **Best Practices**: Evaluate adherence to Solidity best practices

Please be thorough and provide specific recommendations."""

        return {
            "description": f"Analyze contract {contract_address} for {analysis_type} analysis",
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt_text}}
            ],
        }

    def _get_compare_contracts_prompt(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get contract comparison prompt"""
        contract_uids = arguments.get("contract_uids", [])

        prompt_text = f"""You are a smart contract analyst. Please compare the following contracts:

Contract UIDs: {", ".join(contract_uids)}

Provide a detailed comparison covering:

1. **Functionality**: What each contract does and how they differ
2. **Security**: Compare security implementations and potential vulnerabilities  
3. **Architecture**: Analyze design patterns and architectural choices
4. **Similarities**: Identify common code patterns or shared functionality
5. **Differences**: Highlight key differences in implementation
6. **Recommendations**: Suggest which approach is better and why

Please use the contract search tools to gather information about each contract first."""

        return {
            "description": f"Compare contracts: {', '.join(contract_uids)}",
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt_text}}
            ],
        }


# Create FastAPI app
app = FastAPI(
    title="MCP Smart Contract Discovery Server",
    description="Model Context Protocol server for smart contract discovery and analysis",
    version="1.0.0",
)

# Create MCP server instance
mcp_server = MCPServer()


@app.post("/")
async def mcp_handler(request: Request):
    """Main MCP protocol handler"""
    try:
        body = await request.json()

        # Handle single request or batch
        if isinstance(body, list):
            # Batch request
            responses = []
            for req in body:
                response = await process_request(req)
                if response:  # Don't include notifications in batch response
                    responses.append(response)
            return responses
        else:
            # Single request
            response = await process_request(body)
            return response

    except json.JSONDecodeError:
        return create_error_response(None, ErrorCode.PARSE_ERROR.value, "Parse error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return create_error_response(
            None, ErrorCode.INTERNAL_ERROR.value, "Internal error"
        )


async def process_request(req_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a single JSON-RPC request"""
    try:
        # Validate JSON-RPC format
        if req_data.get("jsonrpc") != "2.0":
            return create_error_response(
                req_data.get("id"),
                ErrorCode.INVALID_REQUEST.value,
                "Invalid JSON-RPC version",
            )

        method = req_data.get("method")
        params = req_data.get("params")
        request_id = req_data.get("id")

        # Handle notifications (no id)
        if request_id is None:
            if method == "initialized":
                mcp_server.handle_initialized(params)
            return None

        # Handle requests
        if method == "initialize":
            result = mcp_server.handle_initialize(params or {})
        elif method == "tools/list":
            result = mcp_server.handle_tools_list(params)
        elif method == "tools/call":
            result = mcp_server.handle_tools_call(params or {})
        elif method == "resources/list":
            result = mcp_server.handle_resources_list(params)
        elif method == "resources/read":
            result = mcp_server.handle_resources_read(params or {})
        elif method == "prompts/list":
            result = mcp_server.handle_prompts_list(params)
        elif method == "prompts/get":
            result = mcp_server.handle_prompts_get(params or {})
        else:
            return create_error_response(
                request_id,
                ErrorCode.METHOD_NOT_FOUND.value,
                f"Method not found: {method}",
            )

        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    except MCPError as e:
        return create_error_response(req_data.get("id"), e.code, e.message, e.data)
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return create_error_response(
            req_data.get("id"), ErrorCode.INTERNAL_ERROR.value, str(e)
        )


def create_error_response(
    request_id: Optional[Union[str, int]], code: int, message: str, data: Any = None
) -> Dict[str, Any]:
    """Create a JSON-RPC error response"""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data

    return {"jsonrpc": "2.0", "id": request_id, "error": error}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mcp_version": MCP_VERSION,
        "initialized": mcp_server.initialized,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3030)
