from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.core.data_retrieval.lightweight_retriever import LightweightRetriever
import uvicorn
from src.core.data_access.dgraph_client import DgraphClient
import json
from typing import List, Optional
from fastapi.responses import JSONResponse

app = FastAPI()
retriever = LightweightRetriever()

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

  class Config:
    json_encoders = {
      # Add custom JSON encoders if needed
    }

@app.post("/search")
async def search_contracts(request: SearchRequest):
  try:
    results = retriever.search(request.query, request.limit)
    formatted_results = []
    
    if request.data:
      client = DgraphClient()
      for result in results:
        try:
          contract_data = json.loads(client.get_contract_by_uid(result["metadata"]["dgraph_id"]).json)
          if not contract_data or "contract" not in contract_data or not contract_data["contract"]:
            continue
            
          contract = contract_data["contract"][0]
          formatted_result = ContractResult(
            id=contract["uid"],
            name=contract.get("ContractDeployment.name", ""),
            description=result.get("content", ""),
            created=contract.get("ContractDeployment.created", ""),
            verified=contract.get("ContractDeployment.verified_source", False),
            tags=[contract.get("ContractDeployment.domain", "")],
            storage_protocol=contract.get("ContractDeployment.storage_protocol"),
            storage_address=contract.get("ContractDeployment.storage_address"),
            experimental=contract.get("ContractDeployment.experimental"),
            solc_version=contract.get("ContractDeployment.solc_version"),
            verified_source=contract.get("ContractDeployment.verified_source"),
            verified_source_code=contract.get("ContractDeployment.verified_source_code"),
            functionality=contract.get("ContractDeployment.functionality"),
            domain=contract.get("ContractDeployment.domain"),
            security_risks=contract.get("ContractDeployment.security_risks", [])
          )
          formatted_results.append(formatted_result.model_dump())
        except Exception as e:
          print(f"Error processing contract: {str(e)}")
          continue
      client.close()
    
    return JSONResponse(content=formatted_results)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  
if __name__ == "__main__":
  uvicorn.run(
    app, 
    host="0.0.0.0",  # Allows external access
    port=8000,       # Default port
  )