import os
import sqlite3
import requests
from typing import TypedDict, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

load_dotenv()

DB_NAME = "leads.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lead_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_name TEXT,
            company_name TEXT,
            phone_number TEXT,
            budget INTEGER,
            pain_point TEXT,
            score INTEGER,
            qualification_reason TEXT,
            is_qualified BOOLEAN,
            call_status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_lead_to_db(state: "SDRState"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lead_audit_log (
            lead_name, company_name, phone_number, budget, 
            pain_point, score, qualification_reason, is_qualified, call_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        state["lead_name"],
        state["company_name"],
        state["phone_number"],
        state["stated_budget"],
        state["pain_point"],
        state["qualification_score"],
        state["qualification_reason"],
        state["is_qualified"],
        state["call_status"]
    ))
    conn.commit()
    conn.close()

class LeadEvaluation(BaseModel):
    score: int = Field(description="Score between 0 and 100 evaluating fit")
    reason: str = Field(description="1-sentence rationale for the score")

class SDRState(TypedDict):
    lead_name: str
    company_name: str
    phone_number: str
    stated_budget: int
    pain_point: str
    qualification_score: int
    qualification_reason: str
    is_qualified: bool
    call_status: str

llm = ChatGroq(model="qwen/qwen3.8-27b", temperature=0)
evaluator = llm.with_structured_output(LeadEvaluation)

def qualify_lead_node(state: SDRState) -> dict:
    prompt = f"""
    Evaluate this inbound lead against our Ideal Customer Profile (ICP):
    - ICP Threshold: Minimum budget of $1,000/month and clear automation need.

    Lead Data:
    - Name: {state['lead_name']}
    - Company: {state['company_name']}
    - Stated Budget: ${state['stated_budget']}
    - Need/Pain Point: {state['pain_point']}
    """
    evaluation: LeadEvaluation = evaluator.invoke(prompt)
    is_qual = evaluation.score >= 70
    return {
        "qualification_score": evaluation.score,
        "qualification_reason": evaluation.reason,
        "is_qualified": is_qual
    }

def trigger_voice_call_node(state: SDRState) -> dict:
    vapi_key = os.getenv("VAPI_API_KEY")
    if not vapi_key or vapi_key == "your_vapi_key_here":
        print(f"\n[SIMULATED VAPI CALL] Outbound voice call placed to {state['phone_number']} ({state['lead_name']})...")
        return {"call_status": "dispatched (simulated)"}

    url = "https://api.vapi.ai/call/phone"
    headers = {"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"}
    payload = {
        "customer": {"number": state["phone_number"], "name": state["lead_name"]},
        "assistant": {
            "firstMessage": f"Hi {state['lead_name']}, calling regarding your automation inquiry for {state['company_name']}.",
            "model": {"provider": "groq", "model": "llama-3.1-8b-instant"}
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        return {"call_status": "dispatched" if res.status_code == 201 else f"failed ({res.status_code})"}
    except Exception as e:
        return {"call_status": f"network error: {str(e)}"}

def route_to_nurture_node(state: SDRState) -> dict:
    print(f"\n[NURTURE QUEUE] Lead {state['lead_name']} scored below threshold. Enrolled in nurture email sequence.")
    return {"call_status": "nurture_enrolled"}

def routing_decision(state: SDRState) -> Literal["trigger_voice_call_node", "route_to_nurture_node"]:
    return "trigger_voice_call_node" if state["is_qualified"] else "route_to_nurture_node"

builder = StateGraph(SDRState)
builder.add_node("qualify_lead_node", qualify_lead_node)
builder.add_node("trigger_voice_call_node", trigger_voice_call_node)
builder.add_node("route_to_nurture_node", route_to_nurture_node)

builder.add_edge(START, "qualify_lead_node")
builder.add_conditional_edges("qualify_lead_node", routing_decision)
builder.add_edge("trigger_voice_call_node", END)
builder.add_edge("route_to_nurture_node", END)

sdr_graph = builder.compile()

if __name__ == "__main__":
    init_db()

    qualified_lead = {
        "lead_name": "Tariq Mahmood",
        "company_name": "Nexus Logistics",
        "phone_number": "+923001234567",
        "stated_budget": 2500,
        "pain_point": "Manual dispatching takes 4 hours daily, need automated CRM routing.",
        "qualification_score": 0,
        "qualification_reason": "",
        "is_qualified": False,
        "call_status": "pending"
    }

    print("\n--- PROCESSING LEAD 1 (QUALIFIED) ---")
    state_1 = sdr_graph.invoke(qualified_lead)
    save_lead_to_db(state_1)
    print(f"Outcome: {state_1['call_status']} | Score: {state_1['qualification_score']}/100")

    disqualified_lead = {
        "lead_name": "Hamza Rafiq",
        "company_name": "Solo Print Shop",
        "phone_number": "+923119876543",
        "stated_budget": 150,
        "pain_point": "Looking for free advice on social media marketing tools.",
        "qualification_score": 0,
        "qualification_reason": "",
        "is_qualified": False,
        "call_status": "pending"
    }

    print("\n--- PROCESSING LEAD 2 (DISQUALIFIED) ---")
    state_2 = sdr_graph.invoke(disqualified_lead)
    save_lead_to_db(state_2)
    print(f"Outcome: {state_2['call_status']} | Score: {state_2['qualification_score']}/100")

    print("\n✓ Both leads evaluated and logged to leads.db successfully.")