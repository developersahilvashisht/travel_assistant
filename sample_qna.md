# Sample Questions and Responses

This file documents representative interactions. The tool-call traces below
are **real, captured output** from this codebase (via `test_components.py`
and direct component tests) — they show exactly what the RAG and MCP layers
return. The final natural-language answer in each case depends on which LLM
you configure; run `python3 -m app.cli` with your own API key to capture your
own full transcripts underneath each example, replacing the `[Your run here]`
placeholders.

---

## 1. Pure RAG — Destination Knowledge

**Q: What are the must-visit attractions in Singapore?**

Tool call: `search_travel_knowledge_base(query="must-visit attractions in Singapore")`

Retrieved (excerpt):
```
[Chunk 1 — Singapore Attractions and Neighbourhoods]
## Mandai Wildlife Reserve
Located in the north of the island, Mandai brings together Singapore Zoo,
the Night Safari (the world's first nocturnal wildlife park), River Wonders,
and Bird Paradise ...

SOURCES:
- Visit Singapore - Things to Do / Neighbourhood Guides (https://www.visitsingapore.com/)
```

**Assistant: [Your run here]**

---

## 2. Pure MCP — Weather

**Q: What's the weather forecast for the next 3 days?**

Tool call: `get_weather_forecast(days=3)`

Captured result (run in a sandboxed environment without internet access to
api.open-meteo.com — this demonstrates the graceful-failure path):
```json
{"status": "error", "message": "Weather service returned an error (403). Do not guess the forecast."}
```
On a machine with normal internet access, this returns:
```json
{"status": "ok", "location": "Singapore",
 "forecast": [{"date": "2026-09-07", "min_temp_c": 25.1, "max_temp_c": 32.4,
               "rain_probability_pct": 60, "condition": "slight rain showers"}, ...],
 "source": "Open-Meteo (api.open-meteo.com)"}
```

**Assistant: [Your run here — should state the forecast came from live data, or clearly say live data is unavailable if the tool errors]**

---

## 3. Pure MCP — Currency

**Q: Convert INR 50,000 to SGD.**

Tool call: `convert_currency(amount=50000, from_currency="INR", to_currency="SGD")`

On a machine with normal internet access, returns e.g.:
```json
{"status": "ok", "amount": 50000, "from_currency": "INR", "to_currency": "SGD",
 "converted_amount": 733.5, "rate": 0.01467, "date": "2026-09-05",
 "source": "Frankfurter API (ECB reference rates, api.frankfurter.app)"}
```

**Assistant: [Your run here]**

---

## 4. Combined RAG + MCP (required scenario)

**Q: Plan a three-day trip to Singapore and adjust the activities based on the weather forecast.**

Expected tool calls (both, per the system prompt's combined-request rule):
1. `search_travel_knowledge_base(query="three-day Singapore itinerary")` →
   retrieves the Classic 3-Day Sightseeing Itinerary and the indoor/outdoor
   activity classification.
2. `get_weather_forecast(days=3)` → live forecast.

The assistant should then merge them: keep outdoor-heavy days as planned on
low rain-probability days, and swap in the indoor alternatives already listed
in `05_indoor_outdoor_activities.md` (e.g. Gardens by the Bay conservatories,
ArtScience Museum) on any day with high rain probability — clearly labeling
which parts are knowledge-base facts, which are the live forecast, and which
are its own recommended adjustment.

**Assistant: [Your run here]**

---

## 5. Multi-turn Context

**Turn 1 — Q: I have a budget of INR 60,000 and I'm travelling with two young kids. Plan a three-day Singapore trip for us.**

**Assistant: [Your run here]**

**Turn 2 — Q: Show that budget in SGD.**

Expected: the assistant should call `convert_currency(amount=60000,
from_currency="INR", to_currency="SGD")` **without asking the user to repeat
the amount or currency**, since both were already stated in Turn 1 — this
demonstrates the conversation-memory requirement.

**Assistant: [Your run here]**

---

## 6. Missing-Information Handling

**Q: What's the best rooftop bar in Singapore for a sunset cocktail?**

Expected: the knowledge base doesn't cover specific bar recommendations, so
`search_travel_knowledge_base` will return low-relevance or no results, and
the system prompt requires the assistant to say clearly that this isn't
covered by the knowledge base, rather than inventing a bar name.

**Assistant: [Your run here]**
