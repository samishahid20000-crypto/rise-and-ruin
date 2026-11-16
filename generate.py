import os, json, time, asyncio, requests
import edge_tts

KEY = os.environ["GEMINI_API_KEY"]
TOPIC = "The rise and fall of Nokia"
MODELS = ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]

prompt = f"""You write scripts for the YouTube channel Rise & Ruin (the rise and fall of famous companies and empires). Audience: USA, UK, Canada, Australia. Topic: {TOPIC}.
Return ONLY JSON with keys: title, description, tags (list of strings), script.
The script is spoken narration of about 600 words, with a strong hook in the first line, no stage directions, original wording."""


def ask():
    for attempt in range(4):
        for m in MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                r = requests.post(
                    url,
                    params={"key": KEY},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"responseMimeType": "application/json"},
                    },
                    timeout=120,
                )
            except requests.RequestException as e:
                print(m, "network error", e)
                continue
            if r.status_code == 200:
                print("worked with", m)
                return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
            print(m, r.status_code, r.text[:200])
        time.sleep(20)
    raise SystemExit("All models failed")


data = ask()

os.makedirs("output", exist_ok=True)
with open("output/video.json", "w") as f:
    json.dump(data, f, indent=2)

asyncio.run(edge_tts.Communicate(data["script"], "en-US-GuyNeural").save("output/voice.mp3"))
