# 📞 Autonomous AI SDR & Inbound Voice Triage Agent

An agentic inbound sales automation system built with **LangGraph**, **Groq**, and **Vapi Voice AI**. The agent evaluates inbound leads against Ideal Customer Profile (ICP) criteria, executes conditional routing, triggers automated outbound qualification calls, and maintains an audit ledger in SQLite.

---

## 🏗️ Architecture & Flow

```text
[Inbound Lead Payload]
          │
          ▼
┌──────────────────┐
│ qualify_lead_node│  <── Evaluates ICP fit via Groq (qwen/qwen3.8-27b)
└─────────┬────────┘
          │
  [Conditional Edge]
          │
    ┌─────┴────────────────┐
    ▼ (Score >= 70)        ▼ (Score < 70)
┌──────────────────────┐ ┌─────────────────────┐
│trigger_voice_call_node│ │route_to_nurture_node│
│  (Outbound Vapi Call)│ │   (Email Nurture)   │
└──────────┬───────────┘ └──────────┬──────────┘
           │                        │
           └───────────┬────────────┘
                       ▼
             ┌───────────────────┐
             │ SQLite Audit Log  │ (`leads.db`)
             └───────────────────┘




             