# Demo Script: BLS Public Data MCP Server
## GSA MCP Hackathon — Video Submission (~4 minutes)

---

## PRE-RECORDING SETUP CHECKLIST

Before hitting record, have these tabs/windows open and ready:
- [ ] **Tab 1:** watsonx Orchestrate — chat with **`gsa_ds_bls_baseline_agent`** loaded
- [ ] **Tab 2:** watsonx Orchestrate — chat with **`gsa_ds_bls_agent`** (MCP-augmented) loaded
- [ ] **Tab 3 (optional):** BLS data homepage — https://data.bls.gov/timeseries/
- [ ] Clear any prior conversation history from both agent chats before recording

---

## SECTION 1 — INTRO (0:00–0:40)

**[On screen: Title slide or repo README / blank workspace]**

> "Hi, everyone. My name is Vicky, and I'm here with my colleagues Angel and Ayme. We're all Data Scientists with the Bureau of Labor Statistics.
>
> Today we're walking you through our submission for the government-wide MCP Server Hackathon — a **BLS Public Data MCP Server** built to give AI agents live, structured, and verifiable access to Bureau of Labor Statistics time-series data.
>
> So what does that mean in practice? The BLS is the principal federal agency responsible for measuring labor market activity, working conditions, and price changes in the U.S. economy. It publishes some of the most widely cited economic indicators in the country — the national unemployment rate, the Consumer Price Index, nonfarm payrolls, job openings, wage data, and much more. These series are updated monthly, freely available through the BLS Public Data API, and used every day by researchers, analysts, and decision-makers across government and the private sector.
>
> The BLS organizes its data into dozens of surveys, each with its own series ID format made up of multiple coded segments — a survey prefix, a geographic code, an industry code, a data type code, a seasonal adjustment flag, and more. For a user who is new to BLS data, it can be difficult to know which series actually answers their question.
>
> The challenge is that AI agents, on their own, can't reliably bridge that gap either. Their knowledge is frozen at training time, they can't reach live APIs, and when they try to answer questions about recent BLS statistics, they either hedge or hallucinate. Our MCP server solves both problems at once — it abstracts away the complexity of BLS series structure so that a user can ask a plain-language question and get back a verified, sourced answer, without ever needing to understand the underlying series ID format."

---

## SECTION 2 — THE PROBLEM: BASELINE AGENT (0:40–1:30)

**[Navigate to: watsonx Orchestrate → chat with `gsa_ds_bls_baseline_agent`]**

> "Let's start by showing the problem. Here I have a baseline BLS assistant with no tools — it answers from training data alone. Let me ask it a question that any user might need to answer."

**[TYPE IN CHAT:]**
```
What was the U.S. national unemployment rate for each month of 2024?
```

> "And here's what the baseline returns — something like: *'I'm sorry, but I don't have the monthly unemployment rate figures for 2024. My training data only includes official BLS statistics up through 2023, and I don't have real-time browsing capability to retrieve newer numbers.'*"

**[Pause on the response — let it land]**

> "The model is being honest — and that's actually the best case. It knows what it doesn't know. But the data it's looking for is publicly available right now on the BLS website. The gap isn't in the data — it's in the agent's ability to reach it. That's exactly the problem our MCP server is designed to solve."

---

## SECTION 3 — THE SOLUTION: MCP-AUGMENTED AGENT (1:30–3:00)

**[Navigate to: watsonx Orchestrate → chat with `gsa_ds_bls_agent`]**

> "Now let's switch to our MCP-augmented agent. This is the same LLM — same model — but it's connected to our BLS Public Data MCP Server running on IBM Code Engine. The server exposes twelve tools that give the agent structured, live access to the BLS Public Data API."

**[TYPE IN CHAT — DEMO QUESTION 1:]**
```
What was the U.S. national unemployment rate for each month of 2024?
```

> "Watch what it does now. Instead of guessing from training data, it calls our `answer_bls_question` tool — which is an orchestrator that handles the entire pipeline: it identifies the right BLS series, validates the series ID, fetches live data from the API, and returns the result with full provenance."

**[Pause — point out the tool call chain in the reasoning or response]**

> "We get the actual monthly unemployment rate numbers, sourced directly from the BLS, with the series ID cited — in this case `LNS14000000`, the Current Population Survey unemployment rate — and the agent flags any preliminary values marked with a P footnote."

**[TYPE IN CHAT — DEMO QUESTION 2:]**
```
What is the current annual inflation rate based on the Consumer Price Index?
```

> "Let me ask about inflation. This one is a great example of where the MCP server's data integrity features really shine. Inflation is a measure that people commonly confuse — is it the CPI index level, or the percent change over twelve months?"

**[Pause while tool runs]**

> "The server's ambiguity detection surfaces this distinction. The agent calls our `answer_bls_question` tool, which internally runs an intent parsing step to determine that 'inflation rate' means a twelve-month percent change — not just the index value. It fetches from series `CUUR0000SA0` — the CPI-U All Items — and returns the most recent data with the correct framing."

---

## SECTION 4 — DEPTH: DATA INTEGRITY & DISCOVERY TOOLS (3:00–3:50)

**[Stay in `gsa_ds_bls_agent` chat]**

> "One of the unique things about this MCP server is that it's not just a data fetcher — it's a full data integrity toolkit. Let me show two more tools quickly."

**[TYPE IN CHAT — DEMO QUESTION 3:]**
```
What BLS data is available about job openings and hiring trends?
```

> "When a user doesn't know exactly which series they need, the agent calls our `suggest_series` tool — which searches a curated flagship series catalog locally, with no API call needed. It returns ranked suggestions with the series ID, the survey name, and a plain-language rationale."

**[Pause — point out the ranked suggestions in the response]**

**[TYPE IN CHAT — DEMO QUESTION 4:]**
```
Decode this BLS series ID for me: CES0000000001
```

> "And for data professionals who are working directly with BLS series IDs, the agent can call our `decode_series_id` tool to break down what every segment of a series ID means — the survey, the seasonal adjustment, the industry, the data type. All of this happens locally, with no API call, using our embedded BLS catalog."

**[Pause — point out the decoded segments in the response]**

---

## SECTION 5 — CLOSING (3:50–4:15)

**[Optional: show the BLS data homepage briefly OR return to the presentation slide]**

> "So to summarize — we built a BLS Public Data MCP Server that:
>
> - Gives AI agents **live, structured access** to BLS time-series data across twelve surveys — unemployment, CPI, nonfarm payrolls, job openings, wages, producer prices, and more
> - Includes **data integrity safeguards** — ambiguity detection, series ID validation, and a no-fabrication rule that prevents the model from inventing BLS values
> - Runs on **IBM Code Engine** and integrates natively with watsonx Orchestrate
> - Is **entirely open** — the server code is publicly available and built to be a reusable template for other federal data programs
>
> We hope this demonstrates how an MCP server can close the gap between authoritative government open data and the AI tools that people are already using to do their work. Thank you."

---

## APPENDIX: BACKUP / EXTENDED DEMO QUESTIONS

Use these if you have extra time or want to show additional capabilities:

| Question | Tool it exercises |
|---|---|
| `How many nonfarm payroll jobs were added in the most recent month?` | `answer_bls_question` → CE survey |
| `What is the BLS area code for the Chicago metropolitan area?` | `lookup_area_code` |
| `What industry code does BLS use for the healthcare sector?` | `lookup_industry_code` |
| `Is the series ID LNS14000000 valid?` | `validate_series_id` |
| `Get me the raw data for series CUUR0000SA0 from 2022 to 2024` | `get_series_data` |
| `What was the labor force participation rate in 2023?` | `answer_bls_question` → LN survey |
| `Compare payrolls in January 2020 versus January 2024` | `answer_bls_question` + date range |
| `What does the series ID SMU36356200000000001 describe?` | `decode_series_id` → NYC metro |

---

## TIMING GUIDE

| Section | Target Time | Cumulative |
|---|---|---|
| Intro | 0:40 | 0:40 |
| Baseline agent (problem) | 0:50 | 1:30 |
| MCP agent — Question 1 (unemployment) | 0:45 | 2:15 |
| MCP agent — Question 2 (inflation) | 0:45 | 3:00 |
| Discovery + decode tools | 0:50 | 3:50 |
| Closing | 0:25 | 4:15 |

**Total target: ~4 minutes**

---

## TIPS

- Keep both agent tabs side by side if screen space allows — it makes the contrast more visual
- If a tool call takes more than ~10 seconds, fill the silence by narrating what the tool is doing ("…it's now validating the series ID locally, then making the live API call to BLS…")
- The key narrative contrast is always: **baseline = frozen training data → MCP agent = live verified data**
- Emphasize the series ID citation in every response — it's the proof of provenance that makes the data trustworthy
