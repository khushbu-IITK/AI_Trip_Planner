import os
import re

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 180  # the first plan can take a while (several tool calls)

INTEREST_OPTIONS = [
    "Food", "Beaches", "Adventure", "Culture & history", "Nature",
    "Nightlife", "Shopping", "Relaxation", "Photography",
]
CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "THB"]
PACE_OPTIONS = ["relaxed", "balanced", "packed"]
STAY_OPTIONS = ["budget", "mid-range", "luxury"]
POPULAR = ["Goa", "Jaipur", "Manali", "Kerala", "Rishikesh", "Udaipur", "Bali", "Dubai"]
QUICK_REPLIES = ["Make it cheaper", "Add more food spots", "Swap the hotel", "What should I pack?"]

CSS = """
<style>
.block-container { padding-top: 2.2rem; padding-left: 3rem; padding-right: 3rem; max-width: 100%; }
.hero-sub { opacity: 0.7; margin-top: -0.6rem; margin-bottom: 1.2rem; }
.brand { font-weight: 700; font-size: 1.15rem; }
.side-note { font-size: 0.8rem; opacity: 0.65; }
</style>
"""

st.set_page_config(page_title="TripPlanKro", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------- state helpers -----------------------------
def init_state():
    st.session_state.setdefault("stage", "form")  # "form" | "chat"
    st.session_state.setdefault("thread_id", None)
    st.session_state.setdefault("trip", None)
    st.session_state.setdefault("messages", [])  # [{"role", "content"}]
    st.session_state.setdefault("error", None)  # (kind, message)


def reset_trip():
    st.session_state.stage = "form"
    st.session_state.thread_id = None
    st.session_state.trip = None
    st.session_state.messages = []
    st.session_state.error = None


# ----------------------------- backend calls -----------------------------
def friendly_error(status: int, detail: str):
    """Map a backend failure to (kind, user-facing message)."""
    low = detail.lower()
    if status == 404:
        return "expired", "⌛ Your session expired. Please start a new trip."
    if status == 422:
        return "invalid", f"Please check your input: {detail}"
    if status in (413, 429) or "rate_limit" in low or "rate limit" in low:
        wait = re.search(r"try again in ([\w.]+)", detail)
        extra = f" Try again in {wait.group(1)}." if wait else " Try again in a minute."
        return "rate", "⏳ The AI service hit its rate limit." + extra
    return "server", f"Something went wrong on the server: {detail}"


def call_backend(path: str, payload: dict):
    """POST to the backend. Returns (data, None) or (None, (kind, message))."""
    try:
        resp = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.ConnectionError:
        return None, ("connection", f"🔌 Can't reach the backend at {BACKEND_URL}. Is it running?")
    except requests.exceptions.Timeout:
        return None, ("timeout", "⏱️ The request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        return None, ("server", f"Request failed: {e}")

    if resp.status_code == 200:
        return resp.json(), None

    try:
        body = resp.json()
        detail = body.get("detail", resp.text)
        if isinstance(detail, list):  # FastAPI validation errors
            detail = "; ".join(
                f"{'.'.join(str(p) for p in d.get('loc', [])[1:])}: {d.get('msg')}" for d in detail
            )
    except ValueError:
        detail = resp.text
    return None, friendly_error(resp.status_code, str(detail))


# ----------------------------- sidebar -----------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="brand">🌍 TripPlanKro</div>', unsafe_allow_html=True)
        trip = st.session_state.trip
        if st.session_state.stage == "chat" and trip:
            st.caption("CURRENT TRIP")
            with st.container(border=True):
                st.markdown(f"**{trip['origin']} → {trip['destination']}**")
                st.caption(f"{trip['days']} days · {trip['people']} people")
                badges = []
                if trip.get("budget"):
                    badges.append(f":primary-badge[{trip['currency']} {trip['budget']:,.0f}]")
                badges += [f":primary-badge[{i.title()}]" for i in trip.get("interests", [])]
                if badges:
                    st.markdown(" ".join(badges))
            plan = st.session_state.messages[0]["content"]
            st.download_button(
                "⬇️ Download plan",
                data=plan,
                file_name=f"{trip['destination'].replace(' ', '_').lower()}_trip_plan.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.button("＋ New trip", on_click=reset_trip, use_container_width=True)
        else:
            st.caption("HOW IT WORKS")
            st.write("Tell us where you're going. We'll plan it, then you can refine the plan in chat.")
        st.divider()
        st.markdown(
            '<div class="side-note">AI-generated plans. Check prices and travel rules before you book.</div>',
            unsafe_allow_html=True,
        )


# ----------------------------- stage 1: form -----------------------------
def pick_popular():
    """Popular-destination pill clicked: prefill the To field and clear the pill."""
    dest = st.session_state.get("popular")
    if dest:
        st.session_state.to_city = dest
    st.session_state.popular = None


def render_info_panel():
    with st.container(border=True):
        st.markdown("**What you'll get**")
        st.markdown(
            "- Day-by-day itinerary\n"
            "- Hotels and restaurants with prices\n"
            "- Cost breakdown for your whole group\n"
            "- Weather and local transport\n"
            "- Chat to tweak anything afterwards"
        )
    with st.container(border=True):
        st.markdown("**Popular destinations**")
        st.caption("Tap one to fill the To field")
        st.pills("Popular destinations", POPULAR, selection_mode="single", key="popular",
                 on_change=pick_popular, label_visibility="collapsed")


def render_form():
    left, right = st.columns([3, 2], gap="large")
    with right:
        render_info_panel()
    with left:
        st.title("Where to next?")
        st.markdown('<div class="hero-sub">Four details are enough. Everything else is optional.</div>',
                    unsafe_allow_html=True)

        if st.session_state.error:
            st.error(st.session_state.error[1])
            st.session_state.error = None

        with st.container(border=True):
            with st.form("trip_form", border=False):
                c1, c2 = st.columns(2)
                origin = c1.text_input("From", placeholder="e.g. Delhi", key="from_city")
                destination = c2.text_input("To", placeholder="e.g. Goa", key="to_city")
                c3, c4 = st.columns(2)
                days = c3.number_input("Days", min_value=1, max_value=30, value=3, step=1)
                people = c4.number_input("People", min_value=1, max_value=50, value=2, step=1)

                with st.expander("More preferences (optional)"):
                    b1, b2 = st.columns([2, 1])
                    budget = b1.number_input("Total budget", min_value=0, value=0, step=1000,
                                             help="Leave at 0 if you have no fixed budget")
                    currency = b2.selectbox("Currency", CURRENCIES)
                    interests = st.pills("Interests", INTEREST_OPTIONS, selection_mode="multi") or []
                    p1, p2 = st.columns(2)
                    with p1:
                        pace = st.segmented_control("Pace", PACE_OPTIONS, default="balanced")
                    with p2:
                        stay = st.segmented_control("Stay", STAY_OPTIONS, default="mid-range")

                submitted = st.form_submit_button("Plan my trip", type="primary", use_container_width=True)

    if not submitted:
        return

    if not origin.strip() or not destination.strip():
        st.error("Please fill in both **From** and **To**.")
        return

    payload = {
        "origin": origin.strip(),
        "destination": destination.strip(),
        "days": int(days),
        "people": int(people),
        "currency": currency,
        "interests": [i.lower() for i in interests],
    }
    if budget > 0:
        payload["budget"] = float(budget)
    if pace:
        payload["pace"] = pace
    if stay:
        payload["stay_type"] = stay

    with st.spinner(f"Planning your trip to {payload['destination']}… this can take a minute."):
        data, err = call_backend("/plan", payload)

    if err:
        st.error(err[1])
        return

    st.session_state.thread_id = data["thread_id"]
    st.session_state.trip = payload
    st.session_state.messages = [{"role": "assistant", "content": data["answer"]}]
    st.session_state.stage = "chat"
    st.rerun()


# ----------------------------- stage 2: plan + chat -----------------------------
def queue_question():
    """Pill clicked: queue its text as a follow-up and clear the selection."""
    st.session_state.pending = st.session_state.get("quick")
    st.session_state.quick = None


def render_chat():
    trip = st.session_state.trip
    st.markdown("<style>.block-container { max-width: 1000px; margin: 0 auto; }</style>", unsafe_allow_html=True)

    st.title(f"{trip['origin']} → {trip['destination']}")
    meta = f"{trip['days']} days · {trip['people']} people"
    if trip.get("budget"):
        meta += f" · {trip['currency']} {trip['budget']:,.0f} budget"
    st.caption(meta)

    for m in st.session_state.messages:
        with st.chat_message(m["role"], avatar="🌍" if m["role"] == "assistant" else None):
            st.markdown(m["content"])

    if st.session_state.error:
        kind, msg = st.session_state.error
        st.error(msg)
        if kind == "expired":
            st.button("Start a new trip", on_click=reset_trip, key="expired_new")
        st.session_state.error = None

    st.caption("TRY ASKING")
    st.pills("Quick replies", QUICK_REPLIES, selection_mode="single", key="quick",
             on_change=queue_question, label_visibility="collapsed")

    typed = st.chat_input("Ask a follow-up (e.g. “Add a seafood dinner on day 3”)")
    question = typed or st.session_state.pop("pending", None)
    if not question:
        return

    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="🌍"):
        with st.spinner("Thinking…"):
            data, err = call_backend(
                "/chat", {"thread_id": st.session_state.thread_id, "message": question}
            )

    if err:
        # Don't keep the unanswered question in history; show the error and let the user retry.
        st.session_state.error = err
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append({"role": "assistant", "content": data["answer"]})
    st.rerun()


# ----------------------------- main -----------------------------
init_state()
render_sidebar()
if st.session_state.stage == "form":
    render_form()
else:
    render_chat()
