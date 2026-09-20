# Sample Questions and Responses

## 1. Pure RAG — Destination Knowledge — REAL

**Q: What are the must-visit attractions in Singapore?**

```
  [tool call] search_travel_knowledge_base({'query': 'must visit attractions Singapore'})
  [tool call] search_travel_knowledge_base({'query': 'iconic attractions Singapore Gardens by the Bay Marina Bay Sands Sentosa'})

Assistant: Here are the top must-visit attractions in Singapore, categorized by area and interest:

### 1. Marina Bay & Iconic Skyline
* **Gardens by the Bay:** A futuristic garden attraction situated behind Marina Bay Sands, featuring massive glass conservatories and iconic Supertree structures.
* **Marina Bay Sands:** An iconic integrated resort featuring a luxury hotel, casino, shopping mall, convention centre, and the ArtScience Museum.
* **Singapore Flyer & Esplanade Theatres:** Key landmarks along the waterfront that contribute to Singapore's iconic city skyline.
* **Marina Barrage:** A scenic reservoir dam located at the mouth of the Marina Channel, popular for city views and outdoor relaxation.

### 2. Mandai Wildlife Reserve
* **Bird Paradise:** Asia's largest bird park, home to more than 3,500 birds across 400 species, featuring 10 immersive walk-through aviaries inspired by global habitats.
* **Singapore Zoo, Night Safari & River Wonders:** World-renowned wildlife parks located within the Mandai Wildlife Reserve. The area also features the scenic Mandai Boardwalk along the Upper Seletar Reservoir.

### 3. Sentosa Island & Harbourfront
* **Universal Studios Singapore & Resorts World Sentosa:** A major resort destination featuring theme parks, dining, and entertainment options.
* **AltitudeX:** An indoor skydiving/flight activity located on Sentosa Island for adrenaline seekers.
* **Mount Faber & The Southern Ridges:** Offers an urban treetop walk with local wildlife and scenic views connecting across the harbourfront area.

### 4. Cultural & Nature Heritage
* **Singapore Botanic Gardens:** Singapore's first and only UNESCO World Heritage Site.
* **Civic District & Riverside:** The historic colonial core along the banks of the Singapore River, featuring heritage museums, statues, theatres, and nightlife districts like Boat Quay and Clarke Quay.
* **Pulau Ubin:** A rustic island off the eastern coast near Changi Village that offers a look back at Singapore's traditional rural past.
* **Bukit Timah Nature Reserve:** A lush primary rainforest reserve boasting a vast variety of plant species and local wildlife.
* **Exploria:** One of Southeast Asia's largest indoor, nature-themed multimedia attractions using RFID touchpoints to explore natural realms.

### 5. Shopping & City Life
* **Orchard Road:** Singapore's premier shopping belt, lined with miles of air-conditioned shopping malls and retail centers.

### Sources
* **Visit Singapore - Things to Do:** https://www.visitsingapore.com/things-to-do/top-things-to-do/
* **Wikivoyage Singapore Travel Guide:** https://en.wikivoyage.org/wiki/Singapore
* **Recommendation:** Grouping these attractions by neighbourhood (e.g., Marina Bay in one day, Sentosa in another) is recommended to minimize travel time between sights.
```

**What this confirms:** correct tool selection (RAG tool only, called twice
to broaden the search), answer in real retrieved PDF content, a
proper Sources section citing real URLs, and the model's own suggestion
clearly labeled "Recommendation" rather than presented as a retrieved fact.

---

## 2. Pure MCP — Currency — REAL (includes a real bug found and fixed)

**Q: Convert INR 50000 to SGD**
 [tool call] convert_currency({'from_currency': 'INR', 'to_currency': 'SGD', 'amount': 50000})

Assistant: **INR 50,000** is approximately **SGD 666.71** (at an exchange rate of 1 INR = 0.0133 SGD).

---

### Sources
* Live data: convert_currency (Frankfurter API)
```

**What this confirms:** exactly one tool call a real live exchange rate.
---

## 3. Pure MCP — Weather — REAL

**Q: What's the weather forecast for the next 3 days?**

```
  [tool call] get_weather_forecast({'days': 3})

Assistant: Here is the weather forecast for Singapore for the next 3 days:

### 3-Day Weather Forecast

* **Day 1 (2026-09-18):**
  * **Temperature:** 25.5°C – 32.7°C
  * **Condition:** Dense drizzle
  * **Rain Probability:** 84%

* **Day 2 (2026-09-19):**
  * **Temperature:** 24.3°C – 30.7°C
  * **Condition:** Slight rain showers
  * **Rain Probability:** 90%

* **Day 3 (2026-09-20):**
  * **Temperature:** 24.8°C – 31.2°C
  * **Condition:** Thunderstorm
  * **Rain Probability:** 89%

### Recommendation
* Rain probabilities are high across all three days. It is advisable to keep an umbrella or raincoat handy and prioritize indoor activities or attractions with shelter during peak shower hours.

### Sources
* **Live data:** `get_weather_forecast` (Open-Meteo)
```

**What this confirms:** exactly one tool call, live real forecast data, and
the model's own advice clearly separated under "Recommendation" rather than
mixed into the factual forecast.

---

## 4. Combined RAG + MCP

**Q: Plan a three-day trip to Singapore and adjust the activities based on the weather forecast.**

```
  [tool call] get_weather_forecast({'days': 3})
  [tool call] search_travel_knowledge_base({'query': '3 day itinerary attractions indoor outdoor activities Singapore'})
  [tool call] search_travel_knowledge_base({'query': 'Gardens by the Bay Flower Dome Cloud Forest Jewel Changi museums indoor activities Singapore'})

Assistant: Here is a tailored 3-Day Singapore itinerary that incorporates live weather forecasts and adjusts activities to ensure a smooth trip.

### Weather Overview
* **Day 1 (2026-09-18):** 25.5°C – 32.7°C | **84% rain probability** (*Dense drizzle*)
* **Day 2 (2026-09-19):** 24.3°C – 30.7°C | **90% rain probability** (*Slight rain showers*)
* **Day 3 (2026-09-20):** 24.8°C – 31.2°C | **89% rain probability** (*Thunderstorm*)

### Day 1: Marina Bay & Indoor Nature
* **Morning & Afternoon:** Gardens by the Bay & Marina Bay — explore the indoor, climate-controlled conservatories (Flower Dome and Cloud Forest), then Marina Bay Sands mall / Esplanade.
* **Evening:** Exploria — indoor nature-themed multimedia attraction.
* **Weather Adjustment:** With an 84% chance of drizzle, staying inside the glass domes and connected air-conditioned complexes provides shelter without missing Singapore's famous green spaces.

### Day 2: Culture, Heritage & Museums
* **Morning:** Chinatown — Buddha Tooth Relic Temple and Museum, Sri Mariamman Temple, Masjid Jamae.
* **Afternoon:** Civic District museums and galleries.
* **Evening:** Orchard Road — indoor, air-conditioned shopping malls.
* **Weather Adjustment:** 90% shower probability on Day 2 — spending the afternoon inside Civic District museums keeps you dry during peak rainfall hours.

### Day 3: Indoor Thrills & Jewel Changi
* **Morning:** AltitudeX (indoor skydiving, Sentosa) or Bird Paradise walk-through aviaries.
* **Afternoon & Evening:** Jewel Changi Airport — indoor Rain Vortex waterfall and gardens.
* **Weather Adjustment:** 89% thunderstorm probability — outdoor island activities swapped for AltitudeX and the fully indoor Jewel Changi experience.

### Sources
* **Destination Knowledge Base:**
  * Visit Singapore - Itineraries (https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/)
  * Visit Singapore - Things to Do (https://www.visitsingapore.com/things-to-do/top-things-to-do/)
  * Wikivoyage Singapore Travel Guide (https://en.wikivoyage.org/wiki/Singapore)
* **Live Weather Data:** `get_weather_forecast` (Open-Meteo API)
* **Recommendation:** Swapping outdoor nature walks for climate-controlled conservatories and indoor hubs (Jewel Changi, Exploria, AltitudeX) to adapt to high daily rain probabilities (84%-90%).
```

**What this confirms:** both tool categories called in one turn, and the
results MERGED into a weather-adapted itinerary (outdoor activities
actively swapped for documented indoor alternatives on high-rain days) rather
than the two tool outputs just being concatenated. Sources section correctly
separates knowledge-base citations, live weather data, and the model's own
labeled recommendation.

---

## 5. Multi-turn / Chained Context

**Convert my budget of 60,000 INR to SGD for that trip.**

```
 [tool call] search_travel_knowledge_base({'query': '3 day itinerary attractions indoor outdoor activities'})

  [tool call] get_weather_forecast({'days': 3})

  [tool call] search_travel_knowledge_base({'query': 'Gardens by the Bay Marina Bay Sands museums indoor outdoor attractions Singapore'})

  [tool call] convert_currency({'from_currency': 'INR', 'to_currency': 'SGD', 'amount': 60000})

Assistant: **60,000 INR** is approximately **800.05 SGD** (at an exchange rate of 1 INR = 0.0133 SGD).

This budget of ~800 SGD for a 3-day trip provides about 266 SGD per day, which comfortably covers entry fees to indoor attractions, transport via MRT/taxis, and meals at local hawker centers and restaurants.

### Sources
* **Live data: `convert_currency` (Frankfurter API)**
```

**What this confirms — two findings, one good and one that led to a fix:**

1. **Context retention:.** The model correctly understood
   "that trip" referred to the Turn 1 itinerary, and correctly converted the
   right amount without the user re-stating trip details.
---

## 6. Missing-Information Handling

**Q: What's the best shop for hair cut?**

I do not have any source to provide this information.
---
