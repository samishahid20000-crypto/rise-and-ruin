import os, json, asyncio, requests
import edge_tts

KEY = os.environ["GEMINI_API_KEY"]
TOPIC = "The rise and fall of Nokia"
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

prompt = f"""You write scripts for the YouTube channel Rise & Ruin (the rise and fall of famous companies and empires). Audience: USA, UK, Canada, Australia. Topic: {TOPIC}.
Return ONLY JSON with keys: title, description, tags (list of strings), script.
The script is spoken narration of about 600 words, with a strong hook in the first line, no stage directions, original wording."""

r = requests.post(
    URL,
    params={"key": KEY},
    json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    },
    timeout=120,
)
r.raise_for_status()
data = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])

os.makedirs("output", exist_ok=True)
with open("output/video.json", "w") as f:
    json.dump(data, f, indent=2)

asyncio.run(edge_tts.Communicate(data["script"], "en-US-GuyNeural").save("output/voice.mp3"))
