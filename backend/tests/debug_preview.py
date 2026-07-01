"""Debug preview AI suggest."""
import asyncio
import json
from unittest.mock import MagicMock, patch


async def run():
    from app.routers.preview import ai_suggest, LLMUnavailableError
    mock_request = MagicMock()
    mock_request.state.request_id = "req-1"

    with patch("app.routers.preview.generate_with_fallback", side_effect=LLMUnavailableError("LLM down")):
        response = await ai_suggest(mock_request, "valid-session", "test", "IEEE")

    print(f"type: {type(response)}")
    print(f"has body_iterator: {hasattr(response, 'body_iterator')}")

    events = []
    async for event in response.body_iterator:
        print(f"event type: {type(event)}, value: {str(event)[:200]}")
        events.append(event)
        if event.get("event") == "error":
            d = json.loads(event["data"])
            print(f"  error data: {d}")
            break
        if event.get("event") == "done":
            break
    print(f"Total events: {len(events)}")
    for e in events:
        print(f"  event keys: {list(e.keys())}")
        if isinstance(e, dict) and "data" in e:
            d = json.loads(e["data"])
            print(f"  data keys: {list(d.keys())}, has error: {'error' in d}")


asyncio.run(run())
