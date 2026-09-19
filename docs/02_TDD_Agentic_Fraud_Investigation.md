# TDD — Agentic Fraud Investigation & Next-Best Action

## 1. Purpose

This Technical Design Document defines the architecture and implementation approach for the Agentic Fraud Investigation system described in the PRD.

The system uses TigerGraph as the core graph investigation layer and an AI agent as the orchestration and reasoning layer.

## 2. Architecture Goals

The architecture must:
- Make TigerGraph a primary investigation/evidence source.
- Allow the agent to discover and traverse relevant relationships.
- Separate deterministic graph analysis from LLM reasoning.
- Support uncertainty and additional evidence requests.
- Enforce policy and approval boundaries.
- Maintain complete investigation cases.
- Retrieve relevant historical cases.
- Produce traceable explanations.
- Support evaluation against the 20 benchmark cases.

## 3. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │      Analyst UI      │
                         │ Dashboard / Case UI  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Backend / API      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │      Investigation Agent     │
                    │                              │
                    │ Planner / Reasoner           │
                    │ Evidence Collector           │
                    │ Risk Assessor                │
                    │ Uncertainty Manager          │
                    │ NBA Recommender              │
                    │ Case Manager                 │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
          ┌──────────────────┐          ┌──────────────────┐
          │ TigerGraph MCP   │          │ GraphRAG Layer   │
          └────────┬─────────┘          └────────┬─────────┘
                   │                             │
                   ▼                             ▼
          ┌──────────────────┐          ┌──────────────────┐
          │   TigerGraph     │          │ Policies / Docs  │
          │ Knowledge Graph  │          │ Prior Cases      │
          └──────────────────┘          └──────────────────┘
```

## 4. Component Responsibilities

### 4.1 Analyst UI

Responsibilities:
- Display active cases.
- Display case details.
- Show investigation timeline.
- Show transaction evidence.
- Show graph relationships.
- Show risk and confidence.
- Show uncertainty.
- Show similar historical cases.
- Show agent recommendations.
- Show required approval.
- Allow authorized analyst actions.
- Show investigation reasoning and evidence references.

The UI is a demonstration surface and should make the complete investigation flow visible.

### 4.2 Backend/API

Responsibilities:
- Authenticate users if authentication is implemented.
- Create/open cases.
- Start investigations.
- Stream or return investigation progress.
- Manage agent runs.
- Store application-level state.
- Connect the UI to the agent.
- Provide case and evidence APIs.
- Provide action/approval APIs.

Suggested API groups:

```text
POST   /investigations
GET    /investigations/:id
POST   /investigations/:id/run
GET    /investigations/:id/evidence
GET    /investigations/:id/timeline
GET    /investigations/:id/recommendation
POST   /investigations/:id/evidence-request
POST   /investigations/:id/approve
POST   /investigations/:id/reject
POST   /investigations/:id/execute-action
```

Exact API design can be refined during implementation.

## 5. Agent Architecture

The agent should operate as a controlled investigation loop rather than a single LLM prompt.

### Investigation Loop

```text
TRIGGER
  ↓
LOAD CASE
  ↓
PLAN INVESTIGATION
  ↓
QUERY GRAPH
  ↓
ANALYZE EVIDENCE
  ↓
CHECK PRIOR CASES / POLICIES
  ↓
ASSESS RISK + UNCERTAINTY
  ↓
ENOUGH EVIDENCE?
  ├── NO → REQUEST CONTROLLED EVIDENCE
  │          ↓
  │       RECEIVE EVIDENCE
  │          ↓
  │       REASSESS
  │
  └── YES → DETERMINE NEXT ACTION
              ↓
        CHECK PERMISSION
              ↓
       RECOMMEND / EXECUTE
              ↓
       EXPLAIN DECISION
              ↓
       UPDATE CASE MEMORY
```

## 6. Agent Modules

### 6.1 Investigation Planner

Inputs:
- Trigger
- Transaction/account/case identifier
- Available metadata

Outputs:
- Investigation plan
- Required graph queries
- Evidence priorities

### 6.2 Evidence Collector

Uses TigerGraph MCP tools to gather:
- Transaction history
- Connected accounts
- Devices
- Identity relationships
- Related transactions
- Relevant cases
- Other graph evidence

### 6.3 Graph Analysis Layer

GSQL and TigerGraph graph algorithms perform deterministic analysis.

Potential analysis categories:
- Entity neighborhood exploration
- Multi-hop relationship discovery
- Transaction relationship analysis
- Device/account sharing
- Connected suspicious entities
- Pattern matching
- Historical relationship discovery

The exact algorithms and GSQL queries should be derived from the dataset structure and documented fraud patterns.

### 6.4 Risk & Uncertainty Assessor

Produces structured output:

```json
{
  "risk_level": "...",
  "confidence": 0.0,
  "uncertainty_reasons": [],
  "supporting_evidence": [],
  "contradicting_evidence": [],
  "missing_evidence": [],
  "sufficient_to_act": false
}
```

The confidence value is an assessment of the investigation evidence, not a claim that an LLM probability is ground truth.

### 6.5 Evidence Request Manager

Determines whether controlled additional evidence is appropriate.

Every request should contain:
- Evidence requested
- Reason
- Policy basis
- Expected uncertainty reduction
- Approval requirement

### 6.6 Next-Best-Action Engine

Inputs:
- Risk
- Confidence
- Evidence
- Fraud pattern
- Policy
- Case history
- Permissions

Output:

```json
{
  "recommended_action": "...",
  "reason": "...",
  "approval_required": true,
  "approval_route": "...",
  "supporting_evidence": []
}
```

### 6.7 Case Manager

Maintains:
- Case status
- Findings
- Evidence
- Decisions
- Actions
- Approvals
- Timeline
- Outcome

### 6.8 Memory Retrieval

Retrieves:
- Similar historical cases
- Similar entities
- Similar relationships
- Prior analyst decisions
- Prior outcomes
- Recurring fraud patterns

## 7. TigerGraph Design

TigerGraph is the primary graph investigation layer.

### Required Technology

- TigerGraph Savanna or Community Edition
- GSQL
- TigerGraph graph algorithms
- TigerGraph MCP

The challenge requires graph capabilities to be exposed to the agent through TigerGraph MCP.

## 8. Proposed Graph Model

Initial conceptual graph:

```text
Customer
   │
   └── OWNS ──> Account
                    │
                    ├── MADE ──> Transaction ──> Merchant
                    │
                    └── USED ──> Device
                                      │
                                      └── LINKED_TO ──> Account

Transaction ──> Case
Case ──> Evidence
Case ──> FraudPattern
Case ──> Policy
Case ──> Action
Case ──> SimilarCase
```

This is a conceptual starting point. Exact vertices, edges, attributes, IDs, and source mappings must be based on the dataset README.

## 9. GSQL / Graph Tools

Graph tools should have narrow, predictable responsibilities.

Examples:

```text
get_transaction
get_customer_transactions
get_account_connections
get_device_connections
get_transaction_neighbors
find_related_accounts
find_shared_devices
find_connected_entities
search_similar_cases
run_fraud_pattern_analysis
get_case
write_case
write_evidence
write_action
```

The agent should call tools rather than receiving the entire database.

## 10. TigerGraph MCP

TigerGraph MCP acts as the bridge between the investigation agent and graph capabilities.

Conceptually:

```text
Agent
  ↓
Tool Selection
  ↓
TigerGraph MCP
  ↓
GSQL / Graph Queries
  ↓
TigerGraph
  ↓
Structured Evidence
  ↓
Agent
```

Tool outputs should be structured and concise so the LLM receives relevant evidence rather than unnecessary raw database data.

## 11. GraphRAG Architecture

GraphRAG combines graph evidence with document evidence.

### Document Sources

- Fraud policy
- Fraud procedures
- Fraud typologies
- Regulatory references
- Historical case information where appropriate

### Retrieval Flow

```text
Investigation Context
       ↓
Identify relevant entities/patterns/policy questions
       ↓
Graph retrieval + document retrieval
       ↓
Evidence filtering
       ↓
Context construction
       ↓
LLM reasoning
```

The LLM should receive relevant context rather than the complete raw dataset.

## 12. Policy Engine

Policy should be represented in a structured form where possible.

Example:

```json
{
  "action": "BLOCK_ACCOUNT",
  "conditions": [],
  "approval_required": true,
  "allowed_roles": ["fraud_analyst"],
  "evidence_requirements": []
}
```

The actual policy rules must be derived from the provided fraud policy.

The agent cannot override policy through natural-language reasoning.

## 13. Permission Model

Actions should be classified as:

```text
RECOMMEND_ONLY
HUMAN_APPROVAL
AUTHORIZED_AUTOMATIC
```

The system should check:
1. Is the action permitted?
2. Is required evidence available?
3. Is approval required?
4. Does the current user have permission?
5. Should the action be simulated?

## 14. Case State Machine

Suggested states:

```text
TRIGGERED
   ↓
INVESTIGATING
   ↓
AWAITING_EVIDENCE
   ↓
REASSESSING
   ↓
ACTION_RECOMMENDED
   ↓
AWAITING_APPROVAL
   ↓
ACTION_TAKEN
   ↓
RESOLVED
```

Possible alternate states:
- ESCALATED
- BLOCKED
- CLEARED
- ERROR

The exact final statuses should be aligned with the dataset and product requirements.

## 15. Case Record

A case should contain:

```json
{
  "case_id": "...",
  "trigger": {},
  "status": "...",
  "risk": {},
  "confidence": 0.0,
  "evidence": [],
  "findings": [],
  "fraud_patterns": [],
  "uncertainty": [],
  "evidence_requests": [],
  "recommendations": [],
  "approvals": [],
  "actions": [],
  "timeline": [],
  "similar_cases": [],
  "outcome": {}
}
```

## 16. Explainability Architecture

Each recommendation should be connected to evidence IDs.

```text
Recommendation
   ↓
Evidence IDs
   ↓
Graph Query / Document
   ↓
Underlying Source
```

This allows the UI to show:
- What was found.
- Where it came from.
- Why it matters.
- How it influenced the recommendation.

## 17. LLM Responsibilities

The LLM may perform:
- Investigation planning
- Tool selection
- Evidence synthesis
- Hypothesis generation
- Uncertainty explanation
- Recommendation explanation
- Natural-language case summaries

The LLM should not independently replace:
- Graph traversal
- Deterministic policy checks
- Permission checks
- Case persistence
- Required approval logic

## 18. Reliability Controls

Implement:
- Structured tool schemas
- Structured agent outputs
- Tool-call validation
- Policy validation
- Permission checks
- Evidence references
- Case audit trail
- Error handling
- Retry limits
- Maximum investigation steps
- Investigation stop condition

## 19. Investigation Stop Condition

The agent should stop when:
- Required evidence has been collected.
- Risk and confidence are sufficiently assessed.
- Policy permits a defensible action.
- Required approval route is known.

It should continue or request evidence when:
- Critical uncertainty remains.
- Required evidence is missing.
- Conflicting evidence exists.
- Policy requires additional evidence.

## 20. Benchmark Evaluation Architecture

Run every benchmark case through the same pipeline:

```text
Benchmark Case
     ↓
Agent Investigation
     ↓
Case Record
     ↓
Graph Write
     ↓
Evidence
     ↓
NBA Before Additional Evidence
     ↓
Additional Evidence
     ↓
NBA After Additional Evidence
     ↓
SAR if Required
```

Store outputs in a reproducible format.

## 21. Observability

Record:
- Agent run ID
- Case ID
- Tool calls
- Query names
- Tool inputs/outputs where appropriate
- Evidence IDs
- Agent decisions
- Policy decisions
- Approval events
- Action results
- Errors
- Execution time

This makes debugging and demo reconstruction easier.

## 22. Deployment Concept

For the hackathon:

```text
Frontend
   ↓
Backend
   ↓
Agent Runtime
   ↓
TigerGraph MCP
   ↓
TigerGraph

GraphRAG
   ↓
Policies / Case Knowledge
```

Deployment details can be selected based on available free/hackathon infrastructure.

## 23. Technical Principles

1. Graph-first investigation.
2. Agent as orchestrator, not database replacement.
3. Evidence before conclusion.
4. Explicit uncertainty.
5. Controlled evidence requests.
6. Policy before action.
7. Human approval where required.
8. Every important decision must be explainable.
9. Historical cases should improve future investigations.
10. Every benchmark result must be reproducible.

## 24. Implementation Priority

### P0 — Mandatory
- Dataset ingestion
- TigerGraph graph
- GSQL investigation queries
- TigerGraph MCP
- Agent investigation loop
- Risk/uncertainty assessment
- Next-best-action recommendation
- Case creation/progression
- Graph case write
- Required policy controls
- Benchmark execution
- Basic analyst UI

### P1 — Important
- GraphRAG
- Similar-case retrieval
- Case memory
- Evidence-request workflow
- Approval UI
- Investigation timeline
- Explainability panel

### P2 — Enhancement
- Advanced graph visualization
- Streaming agent activity
- Rich analytics
- Additional external data sources
- More sophisticated memory ranking
- Advanced observability

## 25. Technical Definition of Done

The system is technically complete when:
- The dataset is loaded correctly.
- The graph can retrieve relevant evidence.
- The agent can use TigerGraph through MCP.
- The agent can investigate a case end-to-end.
- The agent can explicitly represent uncertainty.
- The agent can request additional evidence.
- The agent can update its recommendation after new evidence.
- Policy and approval checks are enforced.
- Cases are persisted.
- Relevant prior cases can be retrieved.
- Explanations reference evidence.
- All 20 benchmark cases can be processed.
- Outputs required for submission can be generated.
