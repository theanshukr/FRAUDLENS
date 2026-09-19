# TigerGraph × Hacker House Goa — Fraud Investigation Dataset (IEEE-CIS edition)

Six months of card transactions from the **IEEE-CIS Fraud Detection** dataset, published by Vesta Corporation, with **every original row and every original column kept**. Two things changed: the yes/no fraud label is gone, and every transaction carries a **risk score** from the bank's detection model instead. On top sit the things an investigation needs: customers, a real calendar, a channel, the bank's closed cases, and the 20 cases you'll be judged on.

The data is anonymized by its publisher. No real people.

## The task

Load the data into TigerGraph. Build an agent that takes a case from the case pack, investigates it using the graph and the closed cases, works out **what kind of fraud it is** (if any), **how far it goes**, and **what to do next** under the Fraud Policy section below, and knows when it needs more evidence before deciding. Run it on all 20 cases.

For each case your agent produces **three things**, in one answer file (format in the Answer Format section below):

1. **A case**: the internal investigation record. Status, verdict, pattern, evidence, affected transactions, connected cards, exposure, and the past cases you retrieved. Write it into the graph too. That is your case memory: the next investigation should be able to find it.
2. **A suspicious activity report**, when the policy calls for one: the regulatory filing, written so it stands on its own.
3. **The next best action**: what the bank should do and who must approve it, both before and after any evidence your agent asked for. The recommendation is allowed to change as evidence comes in. Show that it did.

Submit the 20 answer files. We score them against an answer key you don't have.

**Optional.** If your agent also monitors the exam period on its own, picks up alerts from the risk scores, and investigates beyond the 20 cases, put those in a separate folder. They count toward Innovation, not accuracy.

## Start here: your first two hours

1. **Read this document once, top to bottom.** Don't skip the Answer Format; it's what you're graded on.
2. **Get a graph database.** Sign up at https://savanna.tgcloud.io and create a workspace, or install Community Edition from https://dl.tigergraph.com. Both are free. On Savanna, stop the workspace when you're not using it.
3. **Load the two data files.** Suggested schema is in the "Suggested graph schema" section. Start with Customer, Card, Transaction, and the edges between them. Add Device profile, Email domain, Billing region, and ClosedCase once the basics work.
4. **Connect TigerGraph MCP** so your agent can query the graph as tools: https://github.com/tigergraph/tigergraph-mcp
5. **Investigate one case by hand**, before writing any agent code. Pick one from the table at the bottom. Look up the customer's history, the device, the region, the closed cases. Decide what you'd do. Now you know what the agent has to do.
6. **Write your first answer file** for that case, following the example in the Answer Format section. Then automate it.

Questions go to the TigerGraph Discord: https://discord.com/invite/4cc7SNqRf

## Glossary

| Term | Meaning here |
|---|---|
| **Risk score** | A number from 0 to 1 the bank's model attached to every transaction. High means "look at this." It is often wrong in both directions. Never treat it as the answer |
| **Closed case** | An investigation the bank already finished, July to October. Either confirmed fraud or cleared as a false alarm. The only place the truth is written down |
| **Case pack** | The 20 alerts you investigate, all from November and December. Your exam |
| **Trigger** | Why an alert exists: the model scored it high, a customer complained, or an analyst asked |
| **Pattern** | The kind of fraud. Five are documented below. Some in the data are not |
| **Channel** | `in_person` (product code W, no device record) or `online` (all other product codes, device record present) |
| **Identity record** | The device and connection details Vesta captured for online transactions: device type and model, OS, browser, screen, proxy flag, and encoded ratings |
| **Billing region** | `addr1`: an anonymized code for where the card is billed. `addr2` is the country code; 87 is the home country |
| **Exposure** | Total dollars in the fraud episode you identified |
| **Case** (as a deliverable) | The bank's internal record of your investigation. Part 1 of your answer |
| **SAR** | Suspicious Activity Report. The regulatory filing a bank must make for confirmed or strongly suspected fraud above certain thresholds. Part 2 of your answer, only when the policy calls for it |
| **Next best action** | What the bank should do now, and who has to approve it. Part 3 of your answer |
| **Approval route** | `auto` the agent may act alone; `L1` a team lead must approve; `L2` a fraud manager must approve |
| **MCP** | Model Context Protocol. How your agent calls TigerGraph as a set of tools |
| **GraphRAG** | Retrieving evidence from the graph and text from documents, and giving both to the LLM to reason over, instead of raw data |

## Files in this folder

| File | What it is |
|---|---|
| `README.md` | This document: the task, the data, the known patterns, the regulatory references, the fraud policy, the answer format, and the 20 cases |
| `transactions.csv` | 590,742 transactions, all 393 original Vesta columns plus `customer_id`, `ts`, `channel`, `risk_score`. No fraud flag. About 708 MB |
| `identity.csv` | 144,432 identity records, all 41 original columns, joined to transactions on `TransactionID`. Online transactions only |
| `closed_cases_history.csv` | 5,565 finished investigations, July to October. 4,665 confirmed fraud, 900 cleared |
| `case_pack.csv` | The 20 exam cases with their trigger. Also listed at the bottom of this document |

UTF-8 CSV, header row, amounts in USD. `transactions.csv` joins to `identity.csv` on `TransactionID`.

## The original columns, as Vesta describes them

Vesta published the column groups but not the individual definitions. Use them as signals, and be honest in your evidence about what a column is.

| Group | Columns | Meaning |
|---|---|---|
| `TransactionID`, `TransactionDT`, `TransactionAmt` | 3 | ID, seconds from the dataset start, amount in USD |
| `ProductCD` | 1 | Product code: `W`, `C`, `H`, `R`, `S`. `W` transactions have no identity record and are treated as in person |
| `card1` to `card6` | 6 | Card details. `card4` is the network (visa, mastercard, american express, discover), `card6` the type (credit, debit). The others are issuer codes |
| `addr1`, `addr2` | 2 | Billing region and billing country, as codes |
| `dist1`, `dist2` | 2 | Distances between two unnamed points, when known |
| `P_emaildomain`, `R_emaildomain` | 2 | Purchaser and recipient email domains |
| `C1` to `C14` | 14 | Counts, such as how many addresses or phones are associated with the card. Unnamed individually |
| `D1` to `D15` | 15 | Time deltas in days, such as days since the previous transaction. Unnamed individually |
| `M1` to `M9` | 9 | Match flags, such as whether the name on the card matches the address |
| `V1` to `V339` | 339 | Vesta's engineered features: ranking, counting, and relationships between entities. Unnamed |
| `id_01` to `id_11` (identity) | 11 | Encoded ratings: device rating, IP-domain rating, proxy rating, login counts, time on page |
| `id_12` to `id_38` (identity) | 27 | Categorical identity fields. Readable ones: `id_15` (device New / Found), `id_23` (proxy: transparent, anonymous, hidden), `id_30` (OS), `id_31` (browser), `id_33` (screen), `id_34` (match status) |
| `DeviceType`, `DeviceInfo` (identity) | 2 | mobile or desktop; device or platform description, e.g. `SAMSUNG SM-G935F Build/NRD90M` |

## The columns we added

| Column | Meaning |
|---|---|
| `customer_id` | e.g. `C01234`. Derived from the card issuer field; one customer can have several cards. Card IDs in the cases look like `C01234-K1` |
| `ts` | Real timestamp, `YYYY-MM-DD HH:MM:SS`, from July 2 to December 31, 2016 |
| `channel` | `in_person` or `online` |
| `risk_score` | 0 to 1 from the bank's detection model. **An input, not an answer.** Above 0.7, most flagged transactions turn out to be legitimate. Some fraud scores near zero |

`TransactionID`, `card1`, `TransactionDT`, and `TransactionAmt` were disguised (new IDs, small time and amount offsets) so answers cannot be looked up in the public file. Everything else is untouched.

## `closed_cases_history.csv`

`case_id`, `customer_id`, `card_id`, `opened_at`, `closed_at`, `outcome` (`confirmed_fraud` / `cleared`), `pattern`, `first_fraud_txn_id`, `txn_ids` (pipe-separated), `n_txns`, `exposure_usd`, `connected_card_ids`, `actions_taken`, `report_filed`, `analyst_notes`

Patterns are the five below, plus `undocumented` for a few cases the analysts confirmed as fraud but could not match to a known pattern. Read those notes carefully. Cleared cases have `pattern` = `none` and say why the alert was a false alarm.

This file is both your labeled history and your agent's starting memory: retrieve similar past cases when a new alert resembles an old one, cite them in `similar_prior_cases`, and add your own cases to the graph as you close them.

## The case pack

`case_id`, `opened_at`, `trigger_type` (`risk_score` / `customer_report` / `analyst_request`), `trigger_text`, `flagged_txn_id`, `card_id`, `customer_id`, `risk_score` (filled only for risk-score triggers)

The flagged transaction is where the alert fired. It is not necessarily where the fraud started, and it may not be fraud at all.

## The five known fraud patterns

These are the patterns the bank's analysts recognize. **They are not the only patterns in the data.** Noticing activity that fits none of them, describing it in your own words, and recommending a defensible action is scored.

**1. Card testing.** A stolen card number is checked before use: three or more tiny online authorizations, often under $5, then a larger purchase. Confirmed by the sequence itself. Policy R5.

**2. Card-not-present fraud.** The number is used online without the card. Amounts and products that don't fit the cardholder's history, often in a burst of two to four within 48 hours. On its own, one unusual online purchase is ambiguous: verify. Policy R1 to R4.

**3. Card-not-present fraud from a new device.** Same as above, with the identity record marking the device as `New` for this account, sometimes behind a proxy. Stronger than pattern 2, still not proof: people buy new phones.

**4. Out-of-region use.** Card-present purchases in a billing region the cardholder has no history in, while their normal activity continues at home. Several days of purchases in one new region is a trip, not a clone. Policy R2, R3.

**5. Account takeover.** Mixed-channel activity inconsistent with the cardholder, often with device and match-flag anomalies, pointing to stolen credentials rather than a stolen number.

## Regulatory references

Public documents from US and international regulators on fraud typologies, red flags, and how investigations and suspicious activity reports must be written. Load the ones you find useful into TigerGraph's vector store alongside the closed cases and the policy.

**FinCEN (US Treasury)**
- [SAR Filing FAQs, October 2025](https://www.fincen.gov/system/files/2025-10/SAR-FAQs-October-2025.pdf)
- [SAR Narrative Guidance](https://www.fincen.gov/system/files/shared/sar_guidance_narrative.pdf): the standard for your `sar.narrative`
- [Preparing a Complete and Sufficient SAR Narrative](https://www.fincen.gov/system/files/shared/sarnarrcompletguidfinal_112003.pdf)
- [SAR Supporting Documentation (FIN-2007-G003)](https://www.fincen.gov/system/files/shared/fin-2007-g003.pdf)
- [SAR Activity Review: Trends, Tips and Issues](https://www.fincen.gov/sites/default/files/sar_report/sar_tti_19.pdf)
- [Advisory on Account Takeover Activity](https://www.fincen.gov/resources/advisories/fincen-advisory-fin-2011-a016)
- [Advisory on Imposter Scams and Money Mule Schemes](https://www.fincen.gov/system/files/advisory/2020-07-07/Advisory_%20Imposter_and_Money_Mule_COVID_19_508_FINAL.pdf)
- [Identity-Related Suspicious Activity, 2021](https://www.fincen.gov/system/files/shared/FTA_Identity_Final508.pdf)

**FATF**
- [Illicit Financial Flows from Cyber-Enabled Fraud](https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Illicit-financial-flows-cyber-enabled-fraud.pdf.coredownload.inline.pdf)
- [Money Laundering Using New Payment Methods](https://www.fatf-gafi.org/en/publications/Methodsandtrends/Reportonnewpaymentmethods.html)
- [Professional Money Laundering](https://www.fatf-gafi.org/en/publications/Methodsandtrends/Professional-money-laundering.html)
- [Money Laundering through Remittance and Currency Exchange Providers](https://www.fatf-gafi.org/en/publications/Methodsandtrends/Moneylaunderingthroughmoneyremittanceandcurrencyexchangeproviders.html)
- [Trade-Based Money Laundering](https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-trends-and-developments.html)
- [International Co-operation on ML Detection, Investigation and Prosecution](https://www.fatf-gafi.org/en/publications/Methodsandtrends/international-cooperation-against-money-laundering.html)

**FFIEC**
- [Money Laundering and Terrorist Financing Red Flags](https://bsaaml.ffiec.gov/manual/Appendices/07)
- [Suspicious Activity Reporting](https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/04)

**OFAC**
- [Specially Designated Nationals list](https://www.treasury.gov/ofac/downloads/sdnlist.pdf)

## Things to know

- **A risk score is a reason to look.** Never a verdict.
- **Half the cases are legitimate.** Many look suspicious. An agent that blocks everything scores badly.
- **The known patterns are not the only ones.** Some activity in this data fits none of the five. Noticing it and describing it in your own words is scored.
- **Devices and regions connect people.** A device profile or a billing region shared across many cards in a short window is worth a look. Some cases can only be solved by asking what happened on *other* cards.
- **The V, C, D, M and numeric id columns are real model features with no names.** You may use them as signals. Say so in your evidence rather than pretending to know what V127 means.
- **Customer and analyst replies are not provided.** If your agent asks the customer or requests step-up authentication, simulate the response in your own system and record what you assumed in `evidence_requests`.

## Rules

- Use the provided data as the common benchmark. You may extend it with your own data.
- **Do not use the original public IEEE-CIS / Kaggle files to recover outcomes.** IDs, times, and amounts here have been transformed. Doing so is disqualification.
- Every ID in your answer files must exist in this dataset.

## Suggested graph schema

Start here, then change it. Schema design is part of your engineering.

**Vertices:** `Customer`, `Card`, `Transaction`, `DeviceProfile` (DeviceInfo + OS + browser + screen), `EmailDomain`, `BillingRegion`, `ClosedCase`

**Edges:**
- `Customer` → `OWNS` → `Card`
- `Card` → `MADE` → `Transaction`
- `Transaction` → `FROM_DEVICE` → `DeviceProfile` (online only, from `identity.csv`)
- `Transaction` → `PURCHASER_EMAIL` → `EmailDomain`
- `Transaction` → `BILLED_IN` → `BillingRegion` (from `addr1`)
- `Transaction` → `NEXT` → `Transaction` (order by `ts` within a card)
- `ClosedCase` → `INVOLVES` → `Transaction`, `ClosedCase` → `ON_CARD` → `Card`, `ClosedCase` → `CONNECTED_TO` → `Card`

Load the closed-case narratives, this README's pattern section, the policy, and the regulatory documents into TigerGraph vector search for retrieval.

## Attribution

IEEE-CIS Fraud Detection dataset, Vesta Corporation, via the IEEE Computational Intelligence Society. Customers, calendar, channel, risk scores, closed cases, and the case pack were added by TigerGraph for the Hacker House Goa 2026 task. A small number of rows were added to seed investigation exercises.

---

# Fraud Policy

Version 1.0. This is the policy your agent operates under. Action names and approval routes in your case files must use the exact identifiers below.

### 0. What the agent starts with

Every transaction carries a `risk_score` between 0 and 1 from the bank's detection model. The model is useful and imperfect: many high scores are legitimate, and some fraud scores low. A score is a reason to look, never a verdict. The only confirmed outcomes are in the closed cases.

### 1. Actions

| Action | What it does | Customer impact |
|---|---|---|
| `ALLOW_TRANSACTION` | Let the flagged transaction stand | None |
| `DECLINE_TRANSACTION` | Decline the flagged authorization only. Card stays active | Low |
| `MONITOR_CARD` | Card stays active; raise monitoring sensitivity for 72 hours | None |
| `MONITOR_CONNECTED_CARDS` | Put other cards linked to the same device profile, region cluster, or ring under monitoring | None |
| `WARN_CUSTOMER` | Send an informational message (e.g. a recurring charge reminder, a security tip) | None |
| `VERIFY_WITH_CUSTOMER` | Ask the cardholder whether they made the transaction. Card stays active pending reply | Low |
| `STEP_UP_AUTH` | Require a one-time passcode or app confirmation before further activity | Low |
| `BLOCK_CARD` | Block this card and reissue | High |
| `BLOCK_ALL_CARDS` | Block every card the customer holds | Very high |
| `GENERATE_REPORT` | Write up the investigation for the internal record, without opening a case | None |
| `CREATE_CASE` | Open an internal fraud case with the evidence attached, and write it to the graph. See 3a | None |
| `FILE_REPORT` | File a suspicious activity report with the regulator. See 3a | None |
| `ESCALATE_TO_ANALYST` | Hand the case to a human analyst with the evidence | None |
| `CLOSE_NO_FRAUD` | Close the alert as legitimate | None |

An agent may recommend several actions for one case. Order them by what happens first.

### 2. Approval routing

| Route | Applies to |
|---|---|
| `auto` | `ALLOW_TRANSACTION`, `MONITOR_CARD`, `MONITOR_CONNECTED_CARDS`, `WARN_CUSTOMER`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`, `GENERATE_REPORT`, `CREATE_CASE`, `ESCALATE_TO_ANALYST`, `CLOSE_NO_FRAUD` |
| `L1` (team lead) | `DECLINE_TRANSACTION`; `BLOCK_CARD` when exposure ≤ $2,500 |
| `L2` (fraud manager) | `BLOCK_CARD` when exposure > $2,500; `BLOCK_ALL_CARDS` always; `FILE_REPORT` always |

The agent recommends. Only `auto` actions may be executed by the agent. `L1` and `L2` actions are recommended with the route stated and wait for a human.

### 3. Rules

**R1. Verify before you block on a weak signal.** If the case rests on a single signal (including a risk score alone) and your assessed fraud probability is below 0.70, recommend `VERIFY_WITH_CUSTOMER` or `STEP_UP_AUTH` before any block. Blocking a legitimate customer on one signal is a policy breach.

**R2. Customer denies the transaction.** Recommend `BLOCK_CARD` and `CREATE_CASE`. Add `FILE_REPORT` if exposure exceeds $1,000 or the case connects to a shared device profile or another card's fraud.

**R3. Customer confirms the transaction.** Recommend `CLOSE_NO_FRAUD`. Note the confirmation in the case file.

**R4. No reply within 24 hours.** Recommend `MONITOR_CARD` and `DECLINE_TRANSACTION` for pending authorizations. Escalate if exposure exceeds $500.

**R5. Card testing.** Three or more small online authorizations on one card within an hour, followed by a larger purchase: recommend `DECLINE_TRANSACTION` and `STEP_UP_AUTH`. If a purchase over $100 has already cleared, recommend `BLOCK_CARD`.

**R6. Shared origin.** When several cards show fraud from the same device profile, the same billing region, or the same recipient email in one window, name the shared element, recommend `CREATE_CASE` and `FILE_REPORT`, and `MONITOR_CONNECTED_CARDS` for every card that shares it.

**R7. Disputed but legitimate.** When the customer disputes a charge that matches their own recurring pattern (same merchant, same amount, monthly), recommend `CREATE_CASE`, `VERIFY_WITH_CUSTOMER`, and `WARN_CUSTOMER`. Do not block.

**R8. Escalate when uncertain and exposed.** If the verdict is `uncertain` and exposure exceeds $500, or the evidence conflicts, recommend `ESCALATE_TO_ANALYST`.

**R9. Undocumented patterns.** When activity fits none of the known patterns but the evidence shows coordinated or repeated abuse across customers, recommend `CREATE_CASE`, `FILE_REPORT`, and `ESCALATE_TO_ANALYST`, and describe the pattern in your own words. Do not force it into a known category.

**R10. Never `BLOCK_ALL_CARDS`** unless at least two of the customer's cards show confirmed fraud or the customer's credentials are confirmed compromised.

### 3a. A case is not a report

Two different things, and the agent produces both.

**A case** (`CREATE_CASE`) is the bank's internal record of an investigation. Open one whenever fraud probability reaches 0.30, whenever you request evidence, or whenever a customer disputes a charge. A case can be closed as fraud or as legitimate. It can be updated when new evidence arrives. It should be written into the graph so later investigations can find it: a case that names a merchant or a device becomes evidence for the next analyst.

**A suspicious activity report** (`FILE_REPORT`) is a regulatory filing sent outside the bank. File one when fraud is confirmed or strongly suspected **and** at least one of these holds: exposure exceeds $1,000; the activity connects to a shared device profile, a shared region cluster, or another customer's fraud; the pattern is coordinated or undocumented (rule R9). A report always has a case behind it. Most cases never need a report. The report narrative must stand on its own: who, what, when, where, how, and why it is suspicious.

Deciding correctly between "case only" and "case plus report" is part of the next-best-action score.

### 3b. The next best action can change

Recommend what the evidence supports now, then request more evidence if the policy calls for it, then recommend again. Example: probability 0.45 on a single signal, so the initial action is `VERIFY_WITH_CUSTOMER` under R1. The customer denies the transaction. Probability rises, and the final actions become `BLOCK_CARD`, `CREATE_CASE`, and possibly `FILE_REPORT` under R2, with connected cards placed under monitoring. Record both the initial and the final recommendation and what changed between them.

### 4. Exposure

Exposure is the sum of the absolute amounts of every transaction the agent has identified as part of the fraud episode, including the flagged one. Report it in USD.

### 5. Gathering more evidence

The agent may, without approval, ask the customer to validate a transaction, request step-up authentication, or request information from an analyst. In this round those responses are not provided. Simulate them in your own system and state the assumption you made in the case file's `evidence_requests`.

### 6. Stopping

Stop investigating when one of these holds:

- Fraud probability is at or above 0.85, or at or below 0.15, supported by at least two independent pieces of evidence
- A verification response settles the question
- Further steps are unlikely to change the decision. Say so in `stop_reason`

Investigations that continue past a defensible decision waste time. Investigations that stop before one create risk. Both are marked down.

### 7. Explaining

Every recommendation must state what evidence was used, why more evidence was requested if it was, and why the chosen actions follow from this policy. Cite the rule number.

---

# Answer Format

Submit one JSON file per case, named `<case_id>.json`, for every case in `case_pack.csv`. Twenty cases, twenty files, in a folder called `cases/` in your repository.

Each answer has **three parts**, because that is what a fraud investigation produces:

1. **The case.** The bank's internal record of the investigation: its status, what you concluded, what evidence you found, how far the fraud goes, and which past cases you drew on. Cases are internal. They progress as evidence arrives. Your agent should also write the case into the graph so later investigations can find it; that is the case memory the next investigation retrieves.
2. **The suspicious activity report (SAR).** The regulatory filing. Not every case needs one. When your agent recommends `FILE_REPORT`, include the report: who, what, when, where, how, and why it is suspicious. This goes to the regulator, so it must stand on its own.
3. **The next best action.** What the bank should do, with the approval route. Actions evolve: what you recommend before asking the customer may differ from what you recommend after. Record both.

Same structure for every case. Missing fields score zero for that part.

### Fields

#### Top level

| Field | Type | Meaning |
|---|---|---|
| `case_id` | string | From `case_pack.csv` |
| `case` | object | Part 1, below |
| `evidence_requests` | list | Each: `type` (`customer_validation` \| `step_up_auth` \| `analyst_info`), `asked_after_step` (int), `assumed_response` (string). Empty if you asked for nothing |
| `next_best_actions` | object | Part 3, below |
| `sar` | object | Part 2, below |
| `stop_reason` | string | Why the investigation ended here |
| `tool_calls` | int | Graph and retrieval calls made for this case |
| `tokens` | int | LLM tokens consumed for this case |
| `latency_s` | number | Wall-clock seconds for this case |

#### Part 1: `case`

| Field | Type | Meaning |
|---|---|---|
| `status` | `open` \| `closed_fraud` \| `closed_legitimate` \| `escalated` | Where the case stands when your agent stops. `open` means more evidence is still pending |
| `verdict` | `fraud` \| `legitimate` \| `uncertain` | Your conclusion |
| `fraud_probability` | number 0–1 | How likely the flagged activity is fraud. Be honest; this is scored for calibration |
| `pattern` | enum, see below | The fraud pattern you identified, `undocumented` if it matches none of the known ones, or `none` |
| `pattern_description` | string | Required when `pattern` is `undocumented`: two or three sentences on what the pattern is, who it affects, and how you found it. Otherwise `""` |
| `affected_txn_ids` | list of strings | Every transaction you believe is part of the same fraud episode, including the flagged one. Empty if legitimate |
| `first_suspicious_txn_id` | string or `""` | Where it started |
| `connected_card_ids` | list of strings | Other cards caught in the same compromise, ring, or device |
| `connected_device_profiles` | list of strings | Device profiles (DeviceInfo + OS + browser + screen) linking this case to other cards |
| `exposure_usd` | number | Sum of absolute amounts of `affected_txn_ids` |
| `evidence` | list of objects | Each: `claim` (string), `source` (`graph` \| `document` \| `customer` \| `external`), `ref` (query name, document section, or request id), `entity_ids` (list of IDs the claim rests on) |
| `similar_prior_cases` | list of strings | Closed-case IDs from `closed_cases_history.csv` your agent retrieved and used as memory, e.g. `["CC-0141", "CC-2671"]`. Empty if none |
| `summary` | string | Two to six sentences an analyst could read |
| `written_to_graph` | boolean | Whether your agent stored this case in TigerGraph |
| `graph_case_id` | string or `""` | The ID of the case vertex you created, if any |

#### Part 2: `sar`

| Field | Type | Meaning |
|---|---|---|
| `file` | boolean | Whether a suspicious activity report should be filed. Must agree with whether `FILE_REPORT` appears in your final actions |
| `reason` | string | Why file, or why not. Cite the policy rule |
| `narrative` | string | Required when `file` is true. The report itself: **who** (customer, cards, merchants, devices), **what** happened, **when** (dates), **where** (locations, channels), **how** it was carried out, **why** it is suspicious. Six to twelve sentences. This is what a regulator reads |
| `subjects` | list of strings | IDs of the customers, cards, merchants, and devices named in the narrative |
| `total_amount_usd` | number | Total of the suspicious activity |
| `activity_dates` | list of two strings | First and last date of the activity, `YYYY-MM-DD` |

If `file` is false: `narrative` is `""`, `subjects` is `[]`, `total_amount_usd` is 0, `activity_dates` is `[]`.

#### Part 3: `next_best_actions`

| Field | Type | Meaning |
|---|---|---|
| `initial` | list of objects | What you recommended **before** any requested evidence came back. Each: `action` (from the policy), `route` (`auto` \| `L1` \| `L2`), `reason` (cite the policy rule) |
| `final` | list of objects | What you recommend **after** the assumed responses in `evidence_requests`. Same shape. If you requested nothing, `final` equals `initial` |
| `what_changed` | string | One or two sentences on why `final` differs from `initial`, or `"nothing"` |

### `pattern` values

`card_testing` · `card_not_present_fraud` · `card_not_present_new_device` · `out_of_region_use` · `account_takeover` · `undocumented` · `none`

The first five are described in the Known Fraud Patterns section above. Use `undocumented` when the evidence shows abuse that fits none of them, and say what you found in `pattern_description`. Finding an undocumented pattern is scored.

### Example

```json
{
  "case_id": "HHG-017",
  "case": {
    "status": "closed_fraud",
    "verdict": "fraud",
    "fraud_probability": 0.86,
    "pattern": "card_testing",
    "pattern_description": "",
    "affected_txn_ids": ["T0412877", "T0412878", "T0412879", "T0412883"],
    "first_suspicious_txn_id": "T0412877",
    "connected_card_ids": ["C00877-K1"],
    "connected_device_profiles": ["SAMSUNG SM-G892A Build/NRD90M | Android 7.0 | samsung browser 6.2 | 2220x1080"],
    "exposure_usd": 268.43,
    "evidence": [
      {
        "claim": "Three online authorizations under $3 within 40 minutes, then a $259 purchase under a product code this card has never used",
        "source": "graph",
        "ref": "query:card_window(card_id=C00377-K1, hours=2)",
        "entity_ids": ["T0412877", "T0412878", "T0412879", "T0412883"]
      },
      {
        "claim": "All four came from a device profile marked New for this account (Android 7.0, Chrome for Android, 1920x1080), seen on closed case CC-0141 and on card C00877-K1 this month",
        "source": "graph",
        "ref": "query:device_neighbors(device_id=D000731)",
        "entity_ids": ["CC-0141", "C00877-K1"]
      },
      {
        "claim": "Customer denied the purchases when asked",
        "source": "customer",
        "ref": "evidence_request:1",
        "entity_ids": []
      }
    ],
    "similar_prior_cases": ["CC-0141"],
    "summary": "Textbook card testing: three sub-$3 online authorizations in 40 minutes, then a $259 purchase in a category the cardholder has never used. All four share a device profile marked New for this account, which appears on a closed case from August and on another card this month. Customer denied the activity. Card compromised; a second card is likely compromised through the same device.",
    "written_to_graph": true,
    "graph_case_id": "CASE-2016-1187"
  },
  "evidence_requests": [
    { "type": "customer_validation", "asked_after_step": 4, "assumed_response": "Customer states they did not make these purchases and still has the card" }
  ],
  "next_best_actions": {
    "initial": [
      { "action": "DECLINE_TRANSACTION", "route": "L1", "reason": "R5: testing sequence observed, purchase already cleared" },
      { "action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: probability 0.72 on pattern alone, confirm before blocking" }
    ],
    "final": [
      { "action": "BLOCK_CARD", "route": "L1", "reason": "R2 and R5: customer denied; exposure $268 is under $2,500" },
      { "action": "CREATE_CASE", "route": "auto", "reason": "R2" },
      { "action": "FILE_REPORT", "route": "L2", "reason": "R2: shared device links this to another compromised card" },
      { "action": "MONITOR_CONNECTED_CARDS", "route": "auto", "reason": "Same device profile also used on C00877-K1" }
    ],
    "what_changed": "Customer denial raised probability from 0.72 to 0.86 and confirmed the block. The shared device profile with C00877-K1 triggers a report and monitoring of the connected card."
  },
  "sar": {
    "file": true,
    "reason": "R2: confirmed unauthorized use linked by a shared device to a second compromised card",
    "narrative": "On 2016-11-14 between 09:12 and 09:52, card C00377-K1 belonging to customer C00377 was used for three online authorizations of $1.10, $2.40, and $0.95 followed at 10:31 by a $259.98 online purchase under a product code the cardholder had never used. All four transactions came from a device profile marked New for this account, previously recorded on closed case CC-0141 (confirmed fraud, August 2016) and on card C00877-K1 on 2016-11-12. The cardholder, contacted the same day, stated they did not make these purchases and remained in possession of the card. The sequence of small authorizations followed by a larger purchase is consistent with testing of a stolen card number prior to use. The shared device indicates a common actor across at least two cardholders. Total unauthorized amount: $268.43. Card blocked and scheduled for reissue; card C00877-K1 placed under monitoring.",
    "subjects": ["C00377", "C00377-K1", "C00877-K1"],
    "total_amount_usd": 268.43,
    "activity_dates": ["2016-11-14", "2016-11-14"]
  },
  "stop_reason": "Customer denial settled the verdict; device link identified and connected card protected. Further steps would not change the actions.",
  "tool_calls": 9,
  "tokens": 12480,
  "latency_s": 18.7
}
```

### Notes

- IDs must be the ones in the dataset. Made-up IDs score zero.
- For a `legitimate` verdict, `affected_txn_ids` is empty, `exposure_usd` is 0, and `sar.file` is false.
- `uncertain` is a valid verdict and earns full credit on cases designed to be ambiguous, provided the actions follow policy R1 and R8.
- The `risk_score` on the flagged transaction is an input, not an answer. Your `fraud_probability` should reflect what you found, and may be far from it.
- Customer and analyst replies are not provided. State what you assumed in `evidence_requests`, and let `next_best_actions.final` reflect that assumption.
- Keep `summary` short. The evidence list carries the detail. The SAR narrative is the one place to be complete.

---

# The 20 Cases

Also available as `case_pack.csv` in this folder.

| Case | Opened | Trigger | Flagged txn | Card | Customer | Score | Trigger text |
|---|---|---|---|---|---|---|---|
| HHG-001 | 2016-12-05 01:55:28 | risk_score | 3514030 | C12382-K1 | C12382 | 0.61 | Real-time model scored transaction 3514030 ($77.07, in billing region 444.0) at 0.61. Review and decide. |
| HHG-002 | 2016-11-22 23:27:07 | risk_score | 3478782 | C11891-K1 | C11891 | 0.79 | Real-time model scored transaction 3478782 ($292.36, online) at 0.79. Review and decide. |
| HHG-003 | 2016-12-10 15:01:21 | customer_report | 3530164 | C08623-K2 | C08623 | — | Customer C08623 message: 'I never made this $49.00 purchase. Please check my card.' Refers to 3530164. |
| HHG-004 | 2016-12-29 07:53:54 | customer_report | 3583227 | C08106-K1 | C08106 | — | Customer C08106 message: 'I never made this $128.33 purchase. Please check my card.' Refers to 3583227. |
| HHG-005 | 2016-12-08 03:38:37 | risk_score | 3523199 | C02923-K1 | C02923 | 0.54 | Real-time model scored transaction 3523199 ($100.07, online) at 0.54. Review and decide. |
| HHG-006 | 2016-11-22 02:30:00 | customer_report | 3476682 | C07297-K1 | C07297 | — | Customer C07297 message: 'I never made this $482.12 purchase. Please check my card.' Refers to 3476682. |
| HHG-007 | 2016-12-05 03:46:14 | risk_score | 3514948 | C09933-K2 | C09933 | 0.87 | Real-time model scored transaction 3514948 ($111.92, in billing region 264.0) at 0.87. Review and decide. |
| HHG-008 | 2016-12-20 03:08:56 | customer_report | 3558054 | C13171-K2 | C13171 | — | Customer C13171 message: 'I never made this $55.68 purchase. Please check my card.' Refers to 3558054. |
| HHG-009 | 2016-12-28 17:10:53 | customer_report | 3581141 | C08299-K1 | C08299 | — | Customer C08299 message: 'I never made this $30.02 purchase. Please check my card.' Refers to 3581141. |
| HHG-010 | 2016-12-02 18:18:27 | risk_score | 3506725 | C10434-K1 | C10434 | 0.90 | Real-time model scored transaction 3506725 ($1,000.03, online) at 0.90. Review and decide. |
| HHG-011 | 2016-12-29 06:27:44 | customer_report | 3583368 | C11923-K2 | C11923 | — | Customer C11923 message: 'I never made this $131.30 purchase. Please check my card.' Refers to 3583368. |
| HHG-012 | 2016-12-18 05:00:31 | risk_score | 3553342 | C05876-K2 | C05876 | 0.55 | Real-time model scored transaction 3553342 ($30.91, in billing region 494.0) at 0.55. Review and decide. |
| HHG-013 | 2016-12-09 05:39:29 | risk_score | 3526826 | C07671-K2 | C07671 | 0.76 | Real-time model scored transaction 3526826 ($35.66, online) at 0.76. Review and decide. |
| HHG-014 | 2016-11-22 20:11:00 | analyst_request | 3478561 | C13487-K1 | C13487 | — | Analyst request: several cards this month show purchases from the same unusual device profile. Review transaction 3478561 on card C13487-K1 and look for related activity. |
| HHG-015 | 2016-11-17 19:03:36 | risk_score | 3464869 | C03042-K1 | C03042 | 0.77 | Real-time model scored transaction 3464869 ($599.94, online) at 0.77. Review and decide. |
| HHG-016 | 2016-12-12 01:39:08 | customer_report | 3534820 | C09988-K1 | C09988 | — | Customer C09988 message: 'I never made this $59.67 purchase. Please check my card.' Refers to 3534820. |
| HHG-017 | 2016-11-12 00:46:24 | risk_score | 3450629 | C04570-K1 | C04570 | 0.57 | Real-time model scored transaction 3450629 ($100.09, online) at 0.57. Review and decide. |
| HHG-018 | 2016-11-27 14:41:26 | customer_report | 3491361 | C02354-K2 | C02354 | — | Customer C02354 message: 'I never made this $39.08 purchase. Please check my card.' Refers to 3491361. |
| HHG-019 | 2016-12-01 22:28:53 | risk_score | 3503878 | C07987-K2 | C07987 | 0.90 | Real-time model scored transaction 3503878 ($99.92, online) at 0.90. Review and decide. |
| HHG-020 | 2016-12-03 12:04:26 | risk_score | 3509359 | C12265-K2 | C12265 | 0.52 | Real-time model scored transaction 3509359 ($125.08, online) at 0.52. Review and decide. |
