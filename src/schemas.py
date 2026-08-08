from pydantic import BaseModel


class ConversationCreate(BaseModel):
    thread_id: str


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ChatResponse(BaseModel):
    response: str


class UploadResponse(BaseModel):
    filename: str
    chunks: int