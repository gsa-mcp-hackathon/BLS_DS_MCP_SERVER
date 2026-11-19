# Demo Script: BLS Public Data MCP Server
## GSA MCP Hackathon — Video Submission (~3–4 minutes)

---

## PRE-RECORDING SETUP CHECKLIST

Before hitting record, have these tabs/windows open and ready:
- [ ] **Tab 1:** watsonx Orchestrate — chat with **`gsa_ds_bls_baseline_agent`** loaded
- [ ] **Tab 2:** watsonx Orchestrate — chat with **`gsa_ds_bls_agent`** (MCP-augmented) loaded
- [ ] Clear any prior conversation history from both agent chats before recording

---

## SECTION 1 — INTRO (0:00–0:35)

**[On screen: Title slide or repo README / blank workspace]**

> "Hi, everyone. My name is Vicky, and I'm here with my colleagues Angel and Ayme. We're all Data Scientists with the Bureau of Labor Statistics.
>
> Today we're walking you through our submission for the government-wide MCP Server Hackathon — a **BLS Public Data MCP Server** built to give AI agents live, structured, and verifiable access to BLS time-series data. The BLS publishes some of the most widely cited economic indicators in the country — unemployment, CPI, nonfarm payrolls, job openings, and more — but navigating that data isn't always easy. The BLS organizes its data into dozens of surveys, each with its own series ID format made up of multiple coded segments, and for a user who is new to BLS data, it can be difficult to know which series actually answers their question.
>
> The challenge is that AI agents, on their own, can't reliably bridge that gap either. Their knowledge is frozen at training time, they can't reach live APIs, and when they try to answer questions about recent BLS statistics, they either hedge or hallucinate. Our MCP server solves both problems at once — it abstracts away the complexity of BLS series structure so that a user can ask a plain-language question and get back a verified, sourced answer, without ever needing to understand the underlying series ID format."

---

## SECTION 2 — THE PROBLEM: BASELINE AGENT (0:35–1:10)

**[Navigate to: watsonx Orchestrate → chat with `gsa_ds_bls_baseline_agent`]**

> "Let's start by showing the problem. Here I have a baseline BLS assistant with no tools — it answers from training data alone."

**[TYPE IN CHAT:]**
```
What was the U.S. national unemployment rate for each month of 2024?
```

> "And here's what it returns — something like: *'I'm sorry, but I don't have the monthly unemployment rate figures for 2024. My training data only includes official BLS statistics up through 2023, and I don't have real-time browsing capability to retrieve newer numbers.'* The model is being honest — it knows what it doesn't know. But that data is publicly available right now on the BLS website. The gap isn't in the data — it's in the agent's ability to reach it."

---

## SECTION 3 — THE SOLUTION: MCP-AUGMENTED AGENT (1:10–2:50)

**[Navigate to: watsonx Orchestrate → chat with `gsa_ds_bls_agent`]**

> "Now let's switch to our MCP-augmented agent — same model, but connected to our BLS Public Data MCP Server. I'll ask it the same question."

**[TYPE IN CHAT — DEMO QUESTION 1:]**
```
What was the U.S. national unemployment rate for each month of 2024?
```

**[While waiting for the response:]**
> "While it's working — the agent is running our `answer_bls_question` tool, which handles everything automatically: finding the right series, validating it, and making a live call to the BLS API. All from a single plain-language question."

**[Pause — point out the tool call and result]**

> "And we get the actual monthly unemployment rate numbers for 2024, sourced directly from the BLS."

**[TYPE IN CHAT — DEMO QUESTION 2:]**
```
What is the current annual inflation rate based on the Consumer Price Index?
```

> "This one demonstrates another key feature — ambiguity detection. Rather than guessing what I mean by 'inflation rate,' the agent asks which CPI measure I'm interested in: All Items, Food, Energy, or Core CPI. It knows that 'inflation' can mean different things, and it asks before retrieving data rather than silently picking one."

**[ALTERNATIVE — if the agent asks about measure type instead of CPI category:]**
> "This one demonstrates another key feature — ambiguity detection. Rather than guessing what I mean by 'inflation rate,' the agent asks me to clarify what I'm looking for: the raw CPI index level, the month-over-month change, or the 12-month percent change — the year-over-year rate most commonly reported as the annual inflation rate. It surfaces that distinction before making any API call."

**[TYPE IN CHAT — select option (a) or 3 depending on which clarification appears]**
```
a
```
*or*
```
3
```

**[While waiting for the response:]**
> "It's now making the live call to BLS — pulling the real number, straight from the source."

**[Pause — point out the result]**

> "And there it is — the annual inflation rate, sourced directly from the BLS. You'll notice it returns December 2024 as the most recent figure — that's a known LLM behavior where the model can anchor on a date that isn't quite current. The data itself is accurate, but how the model reasons about 'current' is something we're continuing to refine."

---

## SECTION 4 — CLOSING (2:50–3:15)

**[Optional: return to the presentation slide]**

> "So to summarize — we built a BLS Public Data MCP Server that gives AI agents live, structured access to BLS time-series data, with built-in data integrity safeguards like ambiguity detection and series validation. It runs on IBM Code Engine, integrates with watsonx Orchestrate, and is fully open source — built to be a reusable template for other federal data programs. We hope this shows how an MCP server can close the gap between authoritative government open data and the AI tools people are already using. Thank you."

---

## APPENDIX: BACKUP / EXTENDED DEMO QUESTIONS

Use these if you have extra time or want to show additional capabilities:

| Question | Tool it exercises |
|---|---|
| `What BLS data is available about job openings and hiring trends?` | `suggest_series` — discovery |
| `How many nonfarm payroll jobs were added in the most recent month?` | `answer_bls_question` → CE survey |
| `Decode this BLS series ID for me: CES0000000001` | `decode_series_id` |
| `What is the BLS area code for the Chicago metropolitan area?` | `lookup_area_code` |
| `What was the labor force participation rate in 2023?` | `answer_bls_question` → LN survey |

---

## TIMING GUIDE

| Section | Target Time | Cumulative |
|---|---|---|
| Intro | 0:35 | 0:35 |
| Baseline agent (problem) | 0:35 | 1:10 |
| MCP agent — Q1 (unemployment) | 0:45 | 1:55 |
| MCP agent — Q2 (inflation + ambiguity) | 0:55 | 2:50 |
| Closing | 0:25 | 3:15 |

**Total target: ~3–3.5 minutes**

---

## TIPS

- Keep both agent tabs side by side if screen space allows — it makes the contrast more visual
- The key narrative contrast is always: **baseline = frozen training data → MCP agent = live verified data**
- If a tool call takes longer than expected, the filler text under "While waiting for the response" is there to fill the silence naturally
