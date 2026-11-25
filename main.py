import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.agentic_workflow import GraphBuilder
from prompt_library.prompt import build_trip_message
from schemas import AgentResponse, ChatRequest, TripRequest

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # set specific origins in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build the graph ONCE. The checkpointer (conversation memory) lives on this
# graph, so building it per request would wipe the memory every time.
graph = GraphBuilder(model_provider="groq")()


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _thread_exists(thread_id: str) -> bool:
    return bool(graph.get_state(_config(thread_id)).values)


def run_agent(thread_id: str, text: str) -> str:
    """Send one user message into a thread and return the agent's final reply."""
    output = graph.invoke({"messages": [text]}, config=_config(thread_id))
    return output["messages"][-1].content


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/plan", response_model=AgentResponse)
def create_plan(trip: TripRequest):
    """First turn: form -> new thread -> initial plan."""
    thread_id = str(uuid.uuid4())
    try:
        answer = run_agent(thread_id, build_trip_message(trip))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")
    return AgentResponse(thread_id=thread_id, answer=answer)


@app.post("/chat", response_model=AgentResponse)
def chat(req: ChatRequest):
    """Follow-up turn inside an existing thread."""
    if not _thread_exists(req.thread_id):
        raise HTTPException(
            status_code=404,
            detail="Session expired or not found. Please start a new trip.",
        )
    try:
        answer = run_agent(req.thread_id, req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")
    return AgentResponse(thread_id=req.thread_id, answer=answer)
