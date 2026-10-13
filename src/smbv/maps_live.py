"""Live Google Maps review insight via Gemini grounding. Display-only: never written to disk or the database,
shown with Google Maps source links (Maps Platform Service Specific Terms, Maps grounding section)."""
from __future__ import annotations
from smbv.llm import client, model


def review_insight(name: str, address: str, lat: float, lon: float) -> dict:
    from google.genai import types
    cfg = types.GenerateContentConfig(
        temperature=0, tools=[types.Tool(google_maps=types.GoogleMaps())],
        tool_config=types.ToolConfig(retrieval_config=types.RetrievalConfig(lat_lng=types.LatLng(latitude=lat, longitude=lon))))
    q = (f"Using Google Maps information and reviews for {name}, {address}, New York: one short line each on "
         "alcohol service, hours past midnight, outdoor seating, delivery, and any fire, safety or hygiene concerns reviewers mention. "
         "Say 'not mentioned' when the information is not there.")
    r = client().models.generate_content(model=model(), contents=q, config=cfg)
    gm = r.candidates[0].grounding_metadata if r.candidates else None
    sources = [{"title": c.maps.title, "uri": c.maps.uri} for c in (gm.grounding_chunks or []) if getattr(c, "maps", None)] if gm else []
    return {"text": r.text or "", "sources": sources}
