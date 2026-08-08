from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from uuid import uuid4
import shutil
from pathlib import Path
import json

from database import (
      init_db,
      create_or_update_conversation,
      list_conversations,
      get_chat_history,
      conversation_exits,
      save_chat_message
      )
from agent import agent_chat, agent_stream
from schemas import ChatRequest
from rag import add_docs_to_chroma
from config import Config


app = FastAPI(title="ChatAgent API")


Config.STATIC_DIR.mkdir(exist_ok=True)
# Serve static files
app.mount(
    "/static",
    StaticFiles(directory=Config.STATIC_DIR),
    name="static"
)

init_db()


@app.get("/")
def read_index():
    return FileResponse(Config.STATIC_DIR / "index.html")
    

@app.post("/conversations")
async def create_conversation():
   thread_id = str(uuid4())
   create_or_update_conversation(thread_id=thread_id)

   return {
      "thread_id": thread_id,
      "title": "New Chat" 
   }

@app.get("/conversations")
async def get_conversations():
   items = list_conversations()

   return [
        {
            "thread_id": item.thread_id,
            "title": item.title,
            "created_at": item.created_at,
            "updated_at": item.updated_at
        }
        for item in items
    ]


@app.get("/history/{thread_id}")
async def fatch_chat_history(thread_id: str):
   msgs = get_chat_history(thread_id=thread_id)

   return [
      {
         "role": msg.role,
         "content": msg.content,
         "created_at": msg.created_at

      }
      for msg in msgs
   ]


def extract_text_from_message(chunk) -> str:
    """
    Extract plain text from a LangChain message or streamed chunk.

    Supports:
    - Plain string content
    - List[str]
    - List[dict] (Gemini/OpenAI structured responses)
    """

    content = getattr(chunk, "content", "")

    if not content:
        return ""

    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return str(content)

    text_parts = []

    for item in content:
        if isinstance(item, str):
            text_parts.append(item)

        elif isinstance(item, dict):
            text = item.get("text") or item.get("content")
            if isinstance(text, str):
                text_parts.append(text)

    return "".join(text_parts).strip()

@app.post("/chat")
def chat(request: ChatRequest):
   if not conversation_exits(request.thread_id):
      raise HTTPException(
         status_code=404,
         detail="Conversation not found."
      )

   save_chat_message(thread_id=request.thread_id,
                     role="user",
                     content=request.message)

   response = agent_chat(thread_id=request.thread_id, message=request.message)
   response = extract_text_from_message(response)

   save_chat_message(thread_id=request.thread_id,
                     role="assistant",
                     content=response)

   return {
      "response": response
   }

def sse_event(event_type: str, content: str | None = None):
    payload = {"type": event_type}

    if content is not None:
        payload["content"] = content

    return f"data: {json.dumps(payload)}\n\n"

@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
   if not conversation_exits(request.thread_id):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

   save_chat_message(
        thread_id=request.thread_id,
        role="user",
        content=request.message
    )

   def generate():
         full_response = []
         try:
            for chunk in agent_stream(
               thread_id=request.thread_id,
               message=request.message,
               model_name=getattr(request, "model_name", None)
            ):
               if not chunk:
                    continue

               full_response.append(chunk)
               # SSE format: each event is "data: ...\n\n"
               yield sse_event("chunk", chunk)

         except Exception as e:
            yield sse_event("error", str(e))
            return

         finally:
             # Save the complete response to DB after streaming finishes
            if full_response:
                save_chat_message(
                    thread_id=request.thread_id,
                    role="assistant",
                    content="".join(full_response)
               )

            # Signal the client that the stream is done
            yield sse_event("done")

         
   return StreamingResponse(
       generate(),
       media_type="text/event-stream",
       headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # disables nginx buffering if deployed behind it
       }
   )  

            

@app.post("/upload")
def upload_file(thread_id: str=Form(...), file: UploadFile=File(...)):
   
   suffix = Path(file.filename).suffix.lower()
   if suffix not in Config.ALLOWED_EXTENSIONS:
       raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}",
        )

   if not conversation_exits(thread_id):
          raise HTTPException(
             status_code=404,
             detail="Conversation not found."
      )

   # sanitize filename to avoid path traversal and ensure upload dir exists
   safe_filename = Path(file.filename).name
   file_name = f"{uuid4()}_{safe_filename}"
   save_path = Path(Config.UPLOADS_DIR) / file_name

   # ensure upload directory exists and log target path for debugging
   save_path.parent.mkdir(parents=True, exist_ok=True)
   print(f"Saving uploaded file to: {save_path} (cwd={Path.cwd()})")

   with open(save_path, "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)

   # Index into ChromaDB
   try:
      result = add_docs_to_chroma(file_path=str(save_path), thread_id=thread_id)
   except Exception as e:
      save_path.unlink(missing_ok=True)
      raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

   return result