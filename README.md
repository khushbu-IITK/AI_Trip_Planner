# TripPlanKro

AI travel planner: fill a short trip form, get a plan, then chat to refine it.

## Run

Backend (FastAPI):
```
uvicorn main:app --reload --port 8000
```

Frontend (Streamlit):
```
streamlit run streamlit_app.py
```

The frontend talks to `http://localhost:8000` by default. Override with `BACKEND_URL`:
```
BACKEND_URL=http://host:8000 streamlit run streamlit_app.py
```

## API

- `POST /plan`: trip form -> `{thread_id, answer}` (starts a conversation)
- `POST /chat`: `{thread_id, message}` -> `{thread_id, answer}` (follow-up; 404 if the session is gone)
- `GET /health`

Conversation memory is in-process, so restarting the backend ends all sessions.
