import os
import uvicorn
import uuid
import pdb
from fastapi import FastAPI, File, HTTPException, Depends, Body, UploadFile
from typing import List, Optional, Dict, TypeVar, Union
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse

from models.api import (
    UpsertFilesResponse,
    AskQuestionRequest,
    AskQuestionResponse,
)

import uuid
from connectors import FileConnector
from vectorstore import QdrantVectorStore
from llm import get_selected_llm


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to the list of allowed origins if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()
vector_store = QdrantVectorStore()
llm = get_selected_llm()

def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    api_key = os.environ.get("API_KEY")

    if api_key is None:
        return True
    
    if credentials.scheme != "Bearer" or credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing api key")
    return True


@app.post(
    "/upsert-files",
    response_model=UpsertFilesResponse,
)
async def upsert_files(
    files: List[UploadFile] = File(...),
    # auth_success: bool = Depends(validate_token)
):
    try:
        print(files)
        docs = await FileConnector(files).load()
        success = await vector_store.upsert(docs)
        response = UpsertFilesResponse(success=success)
        return response
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/ask-question",
    response_model=AskQuestionResponse,
)
async def ask_question(
    request: AskQuestionRequest = Body(...),
    # auth_success: bool = Depends(validate_token)
):
    try:
        question = request.question
        documents = await vector_store.query(question)
        print(documents)
        answer = await llm.ask(documents, question)
        return AskQuestionResponse(answer=answer)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8080, reload=True)
