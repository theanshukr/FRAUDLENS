"""
FraudLens     Agent Package
========================
LangGraph-based agentic investigation system.

Modules:
    orchestrator          Main LangGraph state machine (investigation loop)
    planner               Build investigation plan from trigger
    evidence_collector     Execute graph queries, collect evidence
    risk_assessor         Assess fraud probability, confidence, pattern
    evidence_request_manager     Determine and generate evidence requests
    nba_engine            Next-Best-Action generation (policy-aware)
    case_manager          Case state machine & persistence
    memory_retrieval      Similar historical case retrieval
"""
