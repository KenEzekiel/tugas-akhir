from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.data_retrieval.lightweight_retriever import LightweightRetriever
import uvicorn

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

@app.post("/search")
async def search_contracts(request: SearchRequest):
  try:
    results = retriever.search(request.query, request.limit)
    return results
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  
if __name__ == "__main__":
  uvicorn.run(
    app, 
    host="0.0.0.0",  # Allows external access
    port=8000,       # Default port
  )