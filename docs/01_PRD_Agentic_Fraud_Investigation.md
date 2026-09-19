# PRD — Agentic Fraud Investigation & Next-Best Action

## 1. Product Overview

Build an AI-powered Fraud Investigation Agent for financial institutions. The agent investigates fraud signals under uncertainty, gathers relevant evidence, creates and progresses investigation cases, determines when enough evidence exists to act, and recommends the next best action.

The solution must use TigerGraph for graph-based investigation and expose graph capabilities to the agent through TigerGraph MCP. GraphRAG should provide relevant graph and document context to the LLM.

## 2. Problem

Fraud analysts currently need to manually:
- Gather transaction history
- Trace money movement
- Identify connected accounts/entities
- Review device and identity signals
- Review policies and previous cases
- Assess risk
- Document findings
- Decide what action to take

The challenge brief describes this process as slow, fragmented, difficult to scale, and often completed after money has already moved.

## 3. Goal

Create an agent that can move from an initial fraud signal to a defensible next action while:
- Using graph relationships as investigation evidence
- Handling uncertainty explicitly
- Requesting additional evidence when required
- Respecting policies and permissions
- Maintaining a complete case record
- Learning from prior investigations
- Explaining evidence, reasoning, uncertainty, and recommended actions

## 4. Target User

### Primary User
Fraud analyst / fraud investigation team.

### User Needs
The analyst needs to:
1. See why a case was triggered.
2. Understand the entities and transactions involved.
3. Inspect connected relationships.
4. See supporting and conflicting evidence.
5. Understand risk and confidence.
6. Know whether more evidence is required.
7. Review the recommended next action.
8. Approve or reject actions when human approval is required.
9. Review the complete investigation history.

## 5. Core Investigation Flow

1. Trigger investigation.
2. Create or open a case.
3. Investigate relevant entities, transactions, relationships, behavior, and prior cases.
4. Gather evidence.
5. Assess risk and uncertainty.
6. Determine whether sufficient evidence exists.
7. If uncertainty remains, request controlled additional evidence.
8. Reassess the case.
9. Recommend or execute the next action according to permissions.
10. Explain the decision.
11. Update case memory with findings, actions, decisions, and outcomes.

## 6. Investigation Triggers

The agent must support investigation triggered by:
- Fraud signal or risk score
- Customer report
- Fraud analyst request
- Another supported event

## 7. Evidence Sources

The agent should be able to use:
- TigerGraph knowledge graph
- Transaction history
- Device signals
- Identity signals
- Account behavior
- Prior fraud cases
- Fraud policies and procedures
- Fraud typologies
- External data sources when available

The challenge dataset contains approximately 590,000 card transactions over six months, approximately 13,500 customers, device/connection records, closed investigations, fraud policy, known fraud patterns, and regulatory references.

## 8. Fraud Assessment

The agent must:
- Identify relevant fraud patterns.
- Determine the likely fraud type when supported by evidence.
- Assess risk.
- Assess confidence/uncertainty.
- Identify missing evidence.
- Determine whether the current evidence is sufficient to act.

The system must not treat an LLM-generated conclusion as a replacement for graph analysis.

## 9. Case Management

Each investigation should maintain:
- Case ID
- Trigger
- Investigation status
- Risk assessment
- Confidence/uncertainty
- Evidence collected
- Findings
- Detected patterns
- Decisions
- Recommended actions
- Approval requirements
- Actions taken
- Investigation timeline
- Final outcome

Cases should be written to the graph as required by the challenge.

## 10. Additional Evidence

When uncertainty remains, the agent may recommend controlled, policy-approved actions such as:
- Asking an account owner to validate a transaction
- Requesting step-up authentication
- Requesting additional information from an analyst or approved party

The system should record:
- Why evidence was requested
- What evidence was requested
- Whether it was received
- How the new evidence changed the assessment

## 11. Next Best Action

Possible actions include:
- Allow transaction
- Block transaction
- Block account
- Monitor account
- Warn customer
- Create fraud case
- File report
- Request additional evidence
- Escalate to fraud analyst

The agent must distinguish between:
- Recommendation
- Authorized automatic execution
- Human approval required

Actions must follow predefined policy and permissions.

## 12. Case Memory

The system must retain relevant information from resolved cases:
- Findings
- Decisions
- Actions
- Outcomes
- Recurring entities
- Recurring relationships
- Recurring fraud patterns
- Analyst decisions

When investigating a new case, the agent should retrieve relevant similar historical cases and use their outcomes to inform recommendations.

## 13. Explainability

Every recommendation should explain:
- Evidence used
- Relevant graph relationships
- Detected patterns
- Risk assessment
- Remaining uncertainty
- Why additional evidence was requested
- Why the selected action was recommended
- Required approval route

The explanation should be traceable to evidence rather than being a generic LLM response.

## 14. User Interface Requirements

The UI must demonstrate:
- Investigation trigger
- Case creation/progression
- Evidence
- Risk and uncertainty
- Graph relationships
- Prior similar cases
- Agent reasoning/explanation
- Recommended next action
- Approval route
- Investigation timeline
- Case outcome

A suitable interface may be an analyst dashboard, conversational interface, case-management view, or combination.

## 15. Required Technology

### Required
- TigerGraph Savanna or Community Edition
- GSQL
- TigerGraph graph algorithms
- TigerGraph MCP
- GraphRAG
- User interface

### Optional
- LangChain
- LangGraph
- OpenAI Agents SDK
- CrewAI
- Custom agent framework
- Additional APIs/data sources

The LLM should primarily perform reasoning, tool selection, evidence synthesis, and explanation.

## 16. Dataset Requirements

The implementation must use the provided HHGOA_IEEE dataset.

Important dataset characteristics:
- Approximately 590,000 transactions
- Approximately 13,500 customers
- Six months of transaction data
- Device and connection records
- Risk score for every transaction
- No direct `Is Fraud` flag
- Closed investigations from the first four months
- Confirmed fraud and cleared cases
- Fraud policy
- Five known fraud patterns
- Regulatory references
- Twenty benchmark cases from the final two months

The dataset README must be treated as the source of truth for exact files, columns, case structure, and answer format.

## 17. Success Criteria

The product should demonstrate that the agent can:
1. Investigate a fraud case from an initial trigger.
2. Gather relevant evidence.
3. Use graph relationships for investigation.
4. Identify fraud patterns and assess risk.
5. Create and progress a case.
6. Recognize insufficient or uncertain evidence.
7. Gather additional evidence when needed.
8. Update recommendations when new evidence arrives.
9. Explain evidence, reasoning, uncertainty, and decisions.
10. Respect policies, permissions, and approvals.
11. Use prior cases as memory.
12. Present the investigation clearly through the UI.

## 18. Hackathon Submission Requirements

The final solution must provide:
- Working agent
- GitHub repository
- Agent output for all 20 provided benchmark cases
- Internal investigation record for each case
- Evidence, findings, decisions, and actions
- Case written to the graph
- Suspicious Activity Report when required by policy
- Next-best-action and approval route before additional evidence
- Updated next-best-action and approval route after additional evidence
- 3–5 minute end-to-end demo
- Technical blog post
- Social media post on X or LinkedIn with the required TigerGraph tag

## 19. Product Boundaries

### In Scope
- Fraud investigation
- Graph-based evidence discovery
- Agentic investigation workflow
- Case management
- Evidence gathering
- Risk/uncertainty assessment
- Next-best-action recommendation
- Policy/approval controls
- Case memory
- Explainability
- Analyst UI
- Benchmark evaluation

### Out of Scope Unless Time Permits
- Production banking integrations
- Real account freezing
- Real card blocking
- Real customer messaging
- Real CRM updates
- Real refunds
- Real regulatory filing

These actions may be simulated, stubbed, or represented through mock APIs as allowed by the challenge.

## 20. Product Principle

The system should not be a generic chatbot placed on top of fraud data.

The core product is an investigation system where:

**Graph evidence + historical cases + policies + agent reasoning → uncertainty assessment → next best action → explainable case record**

The graph remains a primary source of investigative evidence, while the agent orchestrates investigation, reasoning, tool use, evidence gathering, and explanation.
