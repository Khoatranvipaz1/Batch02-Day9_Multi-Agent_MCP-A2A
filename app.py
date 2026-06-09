"""Streamlit chat UI for the distributed Legal Multi-Agent system."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import httpx
import streamlit as st
from dotenv import load_dotenv

from common.a2a_client import delegate

load_dotenv()

CUSTOMER_AGENT_URL = os.getenv(
    "CUSTOMER_AGENT_URL",
    "http://localhost:10100",
)
REGISTRY_URL = os.getenv("REGISTRY_URL", "http://localhost:10000")

SERVICES = {
    "Registry": f"{REGISTRY_URL}/health",
    "Customer": f"{CUSTOMER_AGENT_URL}/.well-known/agent.json",
    "Law": "http://localhost:10101/.well-known/agent.json",
    "Tax": "http://localhost:10102/.well-known/agent.json",
    "Compliance": "http://localhost:10103/.well-known/agent.json",
}


async def ask_customer_agent(question: str, context_id: str, trace_id: str) -> str:
    """Send one user question through the existing A2A agent network."""
    return await delegate(
        endpoint=CUSTOMER_AGENT_URL,
        question=question,
        context_id=context_id,
        trace_id=trace_id,
        depth=0,
    )


async def check_services() -> dict[str, bool]:
    """Check local service availability without invoking any LLM."""
    statuses: dict[str, bool] = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, url in SERVICES.items():
            try:
                response = await client.get(url)
                statuses[name] = response.is_success
            except httpx.HTTPError:
                statuses[name] = False
    return statuses


st.set_page_config(page_title="Legal Multi-Agent A2A", layout="wide")
st.title("Legal Multi-Agent A2A")
st.caption(
    "Customer Agent routes questions to Law, Tax, and Compliance agents "
    "through the A2A protocol."
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_id" not in st.session_state:
    st.session_state.context_id = str(uuid4())
if "trace_id" not in st.session_state:
    st.session_state.trace_id = str(uuid4())

with st.sidebar:
    st.subheader("Agent Network")
    if st.button("Check services", use_container_width=True):
        with st.spinner("Checking local services..."):
            st.session_state.service_statuses = asyncio.run(check_services())

    statuses = st.session_state.get("service_statuses", {})
    if statuses:
        for name, online in statuses.items():
            st.write(f"{'Online' if online else 'Offline'}: {name}")
    else:
        st.caption("Use Check services before sending a question.")

    st.divider()
    st.caption(f"Context: `{st.session_state.context_id[:8]}`")
    st.caption(f"Trace: `{st.session_state.trace_id[:8]}`")

    if st.button("New conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.context_id = str(uuid4())
        st.session_state.trace_id = str(uuid4())
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask a legal, tax, or compliance question...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agents are collaborating..."):
            try:
                answer = asyncio.run(
                    ask_customer_agent(
                        prompt,
                        context_id=st.session_state.context_id,
                        trace_id=st.session_state.trace_id,
                    )
                )
                if not answer:
                    answer = "The agent network returned an empty response."
            except Exception as exc:
                answer = (
                    "Could not reach the agent network. Start the services with "
                    f"`./start_all.ps1` and try again.\n\nDetails: `{exc}`"
                )
        st.markdown(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
