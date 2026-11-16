import os, json, time, asyncio, subprocess, textwrap, requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont

KEY = os.environ["GEMINI_API_KEY"]
PIX = os.environ["PIXABAY_API_KEY"]
TOPIC = "The rise and fall of Nokia"
MODELS = ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
W, H = 1280, 720

prompt = f"""You write scripts for the YouTube channel Rise & Ruin (the rise and fall of famous companies and empires). Audience: USA, UK, Canada, Australia. Topic: {TOPIC}.
Return ONLY JSON with keys: title, description, tags (list of strings), script, scenes.
The script is spoken narration of about 600 words, with a strong hook in the first line, no stage directions, original wording.
scenes is a list of exactly 20 short English search phrases (2 or 3 words each) for stock footage, in story order, matching the script. Use generic visuals such as old mobile phone, factory workers, stock market, business meeting, city skyline. Never use brand names or people's names."""


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


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-1500:])
        raise SystemExit("command failed: " + cmd[0])
    return p.stdout


def duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


def find_media(q, used):
    try:
        r = requests.get("https://pixabay.com/api/videos/",
                         params={"key": PIX, "q": q, "per_page": 6, "safesearch": "true"}, timeout=30)
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                v = hit.get("videos", {})
                pick = v.get("medium") or v.get("small") or v.get("tiny")
                if pick and pick.get("url") and pick["url"] not in used:
                    return "video", pick["url"]
        r = requests.get("https://pixabay.com/api/",
                         params={"key": PIX, "q": q, "image_type": "photo",
                                 "orientation": "horizontal", "per_page": 6, "safesearch": "true"}, timeout=30)
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                if hit["largeImageURL"] not in used:
                    return "image", hit["largeImageURL"]
    except Exception as e:
        print("search error", q, e)
    return None


def download(url, path):
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


VF = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setsar=1"
ENC = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p"]

data = ask()
os.makedirs("output", exist_ok=True)
os.makedirs("build/clips", exist_ok=True)
with open("output/video.json", "w") as f:
    json.dump(data, f, indent=2)

asyncio.run(edge_tts.Communicate(data["script"], "en-US-GuyNeural", rate="-12%").save("output/voice.mp3"))

total = duration("output/voice.mp3")
scenes = data.get("scenes") or ["city skyline"]
d = round(total / len(scenes) + 0.05, 2)
print("voice seconds", total, "scenes", len(scenes), "each", d)

used, clips = set(), []
for i, q in enumerate(scenes):
    out = f"build/clips/c{i:02d}.mp4"
    found = find_media(q, used)
    time.sleep(0.5)
    if found:
        kind, url = found
        used.add(url)
        src = f"build/clips/src{i:02d}" + (".mp4" if kind == "video" else ".jpg")
        try:
            download(url, src)
            if kind == "video":
                run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", str(d), "-vf", VF] + ENC + [out])
            else:
                run(["ffmpeg", "-y", "-loop", "1", "-i", src, "-t", str(d), "-vf", VF] + ENC + [out])
            clips.append(out)
            print("scene", i, q, kind)
            continue
        except BaseException as e:
            print("scene failed", i, q, e)
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x111111:s={W}x{H}:d={d}:r=30"] + ENC + [out])
    clips.append(out)
    print("scene", i, q, "plain background")

with open("build/list.txt", "w") as f:
    for c in clips:
        f.write(f"file '{os.path.abspath(c)}'\n")

run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "build/list.txt", "-c", "copy", "build/joined.mp4"])
run(["ffmpeg", "-y", "-i", "build/joined.mp4", "-i", "output/voice.mp3",
     "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", "build/video.mp4"])

# thumbnail
run(["ffmpeg", "-y", "-ss", "1", "-i", clips[0], "-frames:v", "1", "build/frame.jpg"])
img = Image.open("build/frame.jpg").convert("RGB").resize((W, H))
img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), 0.5)
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
except Exception:
    font = ImageFont.load_default()
lines = textwrap.wrap(data["title"].upper(), 18)[:4]
y = (H - len(lines) * 110) // 2
for line in lines:
    w = draw.textlength(line, font=font)
    draw.text(((W - w) / 2, y), line, font=font, fill=(245, 197, 66), stroke_width=6, stroke_fill=(0, 0, 0))
    y += 110
img.save("build/thumbnail.jpg", quality=92)
print("DONE")
