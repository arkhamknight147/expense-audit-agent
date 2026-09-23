# Grey clauses — PRIVATE eval note

> **Do not include this file in any prompt, retrieval index or agent context.** It exists only to design and label the judgement slice of the golden set (EVAL_PLAN §2). If the agent can see which clauses are grey, the judgement evals are contaminated.

| Clause | Where the ambiguity is | Example judgement case | Expected handling |
|---|---|---|---|
| HTL-03 Weekend stays | "More economical" and "business needs" are not quantified | Stayed Fri–Mon in Hyderabad; meetings Fri and Mon; flight home Fri night was ₹9,000 | Escalate with citation |
| ENT-01 Client entertainment | Who counts as a "prospective client"; what "develop a relationship" means | Dinner with a former colleague now at a potential partner firm | Escalate |
| ENT-02 Team meals | What counts as a "celebration"; whether approval must be written | "Sprint closure dinner", approval mentioned only in the justification text | Escalate |
| ENT-03 Alcohol with clients | "Reasonable and appropriate" is undefined | Bar bill ₹6,000 for 2 attendees at a client dinner | Escalate |
| TRN-02 Premium cabs | "Otherwise necessary for business" is open-ended | SUV cab at 18:00, justification "carrying demo equipment" | Escalate |
| AIR-02 Advance booking | "Wherever practicable"; quality of the reason | Booked 2 days ahead, reason "client meeting confirmed late" | Escalate |
| MISC-02 Incidental expenses | "Reasonably necessary" catch-all | Umbrella purchase ₹450 during monsoon site visit | Escalate |

Labelling rule: for grey cases the expected decision is `escalate` unless the PM judges the case clearly compliant or clearly non-compliant under a plain reading. The PM records the reasoning in the label so the LLM judge (Q6) can be calibrated against it.
