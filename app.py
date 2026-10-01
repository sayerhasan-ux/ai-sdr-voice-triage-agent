import sqlite3
import streamlit as st
from agent import sdr_graph, save_lead_to_db, init_db

init_db()

st.set_page_config(
    page_title="AI SDR & Voice Triage Agent",
    page_icon="📞",
    layout="wide"
)

st.title("📞 Autonomous AI SDR & Inbound Voice Triage Agent")
st.caption("Deterministic Lead Qualification (LangGraph + Groq) & Outbound Voice Dispatch (Vapi)")

col_left, col_right = st.columns([1, 1.2], gap="large")

with col_left:
    st.subheader("📥 Inbound Lead Intake")
    with st.form("lead_form"):
        lead_name = st.text_input("Lead Full Name", placeholder="e.g. John Doe")
        company_name = st.text_input("Company Name", placeholder="e.g. Acme Corp")
        phone_number = st.text_input("Phone Number", placeholder="e.g. +1 555 123 4567")
        stated_budget = st.number_input("Stated Monthly Budget ($)", min_value=0, value=0, step=100)
        pain_point = st.text_area(
            "Primary Bottleneck / Need",
            placeholder="Describe operational bottleneck, manual workload, or CRM requirements..."
)
        
        submitted = st.form_submit_button("⚡ Evaluate & Triage Lead", use_container_width=True)

with col_right:
    st.subheader("📊 Autonomous Triage Result")
    
    if submitted:
        payload = {
            "lead_name": lead_name,
            "company_name": company_name,
            "phone_number": phone_number,
            "stated_budget": int(stated_budget),
            "pain_point": pain_point,
            "qualification_score": 0,
            "qualification_reason": "",
            "is_qualified": False,
            "call_status": "pending"
        }
        
        with st.spinner("Invoking LangGraph ICP Scoring Engine..."):
            final_state = sdr_graph.invoke(payload)
            save_lead_to_db(final_state)
            
        score = final_state["qualification_score"]
        is_qual = final_state["is_qualified"]
        
        # Display Metrics
        m1, m2 = st.columns(2)
        m1.metric("ICP Fit Score", f"{score} / 100")
        m2.metric("Triage Decision", "QUALIFIED" if is_qual else "DISQUALIFIED")
        
        if is_qual:
            st.success(f"**Action Executed:** {final_state['call_status'].title()}")
        else:
            st.warning(f"**Action Executed:** {final_state['call_status'].title()}")
            
        st.info(f"**Agent Rationale:** {final_state['qualification_reason']}")

st.divider()

st.subheader("🗄️ Database Audit Ledger (`leads.db`)")
conn = sqlite3.connect("leads.db")
cursor = conn.cursor()
cursor.execute("""
    SELECT id, lead_name, company_name, budget, score, is_qualified, call_status, timestamp 
    FROM lead_audit_log ORDER BY id DESC LIMIT 10
""")
records = cursor.fetchall()
conn.close()

if records:
    columns = ["ID", "Lead Name", "Company", "Budget ($)", "Score", "Qualified", "Action Status", "Logged At"]
    formatted_records = [dict(zip(columns, row)) for row in records]
    st.dataframe(formatted_records, use_container_width=True)
else:
    st.write("No leads logged yet.")