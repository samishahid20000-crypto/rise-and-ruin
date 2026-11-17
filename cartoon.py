import os, json, math, time, asyncio, subprocess, textwrap, urllib.parse, requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont

KEY = os.environ["GEMINI_API_KEY"]
TOPIC = "The rise and fall of Nokia"
WORDS = 80
MODELS = ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
W, H, FPS = 1280, 720, 30
SEG = 4.9
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
STYLE = "flat colorful 2D cartoon illustration, bold black outlines, vibrant colors, simple clean background, no text, no letters, no watermark"


def ask(prompt):
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
                try:
                    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
                except Exception as e:
                    print(m, "bad json", e)
                    continue
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


async def tts(text, path):
    try:
        comm = edge_tts.Communicate(text, "en-US-GuyNeural", rate="-12%", boundary="WordBoundary")
    except TypeError:
        comm = edge_tts.Communicate(text, "en-US-GuyNeural", rate="-12%")
    marks = []
    with open(path, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] in ("WordBoundary", "SentenceBoundary"):
                marks.append((ch["offset"] / 1e7, ch["duration"] / 1e7, ch["text"]))
    return marks


def build_segments(marks, words, total):
    segs = []
    if len(marks) >= 0.5 * len(words):
        start, text = 0.0, []
        for off, dur, w in marks:
            if text and (off + dur - start) > SEG - 0.7:
                segs.append((start, off, " ".join(text)))
                start, text = off, []
            text.append(w)
        if text:
            segs.append((start, total, " ".join(text)))
        print("using exact word timing")
    else:
        n = math.ceil(total / SEG)
        for i in range(n):
            a, b = round(i * len(words) / n), round((i + 1) * len(words) / n)
            segs.append((total * i / n, total * (i + 1) / n, " ".join(words[a:b])))
        print("word timing missing, using even split")
    final = []
    for a, b, t in segs:
        k = max(1, math.ceil((b - a) / SEG))
        for j in range(k):
            final.append((a + (b - a) * j / k, a + (b - a) * (j + 1) / k, t))
    return final


def gen_image(prompt, path, w=W, h=H, seed=1):
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:400])
    for attempt in range(5):
        try:
            r = requests.get(url, params={"width": w, "height": h, "seed": seed + attempt,
                                          "nologo": "true"}, timeout=180)
            time.sleep(16)
            if r.status_code == 200 and len(r.content) > 5000:
                with open(path + ".raw", "wb") as f:
                    f.write(r.content)
                Image.open(path + ".raw").convert("RGB").save(path, quality=92)
                return True
            print("image status", r.status_code, len(r.content))
        except Exception as e:
            print("image error", e)
        time.sleep(10)
    return False


def make_card(text, path):
    img = Image.new("RGB", (W, H), (17, 17, 17))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT, 80)
    except Exception:
        font = ImageFont.load_default()
    lines = textwrap.wrap(text.upper(), 20)[:3]
    y = (H - len(lines) * 100) // 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=(245, 197, 66))
        y += 100
    img.save(path, quality=92)


def get_prompts(texts):
    p = f"""Video topic: {TOPIC}. Below are consecutive narration lines of a cartoon documentary. For each line write an image prompt (max 30 words) describing exactly ONE clear scene of what that line talks about, so the main subject of the line is the main subject of the picture (if the line mentions a phone, a phone is shown; towers, towers; money, money). Keep the same characters and look in all images. Do not put any text or letters in the images. Return ONLY a JSON list of exactly {len(texts)} strings in the same order.

""" + "\n".join(f"{i + 1}. {c}" for i, c in enumerate(texts))
    res = ask(p)
    if not isinstance(res, list):
        res = []
    res = [str(x) for x in res][:len(texts)]
    while len(res) < len(texts):
        res.append(texts[len(res)])
    return res


def motion(i, frames):
    big = "scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440"
    tail = f"d={frames}:s={W}x{H}:fps={FPS},setsar=1"
    m = i % 3
    if m == 0:
        z = f"zoompan=z='min(zoom+0.0007,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':{tail}"
    elif m == 1:
        z = f"zoompan=z='max(1.12-0.0007*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':{tail}"
    else:
        z = f"zoompan=z=1.12:x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':{tail}"
    return big + "," + z


prompt = f"""You write scripts for the YouTube channel Rise & Ruin (the rise and fall of famous companies and empires), cartoon documentary style. Audience: USA, UK, Canada, Australia. Topic: {TOPIC}.
Return ONLY JSON with keys: title, description, tags (list of strings), script, thumb_text, thumb_prompt.
script: spoken narration of about {WORDS} words, strong hook in the first line, no stage directions, original wording.
thumb_text: 2 to 4 words in capital letters, very punchy, for a thumbnail.
thumb_prompt: one dramatic cartoon scene (max 30 words) showing the main subject of the video, no text."""

data = ask(prompt)
os.makedirs("output", exist_ok=True)
os.makedirs("build/clips", exist_ok=True)
with open("build/video.json", "w") as f:
    json.dump(data, f, indent=2)

words = data["script"].split()
marks = asyncio.run(tts(data["script"], "build/voice.mp3"))
total = duration("build/voice.mp3")
segs = build_segments(marks, words, total)
print("voice seconds", total, "images", len(segs))

prompts = get_prompts([s[2] for s in segs])

clips = []
prev_frames = 0
for i, ((a, b, text), pr) in enumerate(zip(segs, prompts)):
    end_frames = round(b * FPS)
    frames = max(2, end_frames - prev_frames)
    prev_frames = end_frames
    img = f"build/clips/i{i:02d}.jpg"
    out = f"build/clips/c{i:02d}.mp4"
    if gen_image(pr + ", " + STYLE, img, seed=100 + i * 7):
        print("image", i, pr)
    else:
        make_card(text[:40], img)
        print("image", i, "text card")
    run(["ffmpeg", "-y", "-i", img, "-vf", motion(i, frames), "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", out])
    clips.append(out)

with open("build/list.txt", "w") as f:
    for c in clips:
        f.write(f"file '{os.path.abspath(c)}'\n")

run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "build/list.txt", "-c", "copy", "build/joined.mp4"])
run(["ffmpeg", "-y", "-i", "build/joined.mp4", "-i", "build/voice.mp3",
     "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", "build/video.mp4"])

# thumbnail: cartoon picture + bold text
bg = "build/thumb_bg.jpg"
tp = data.get("thumb_prompt") or data["title"]
if not gen_image(tp + ", " + STYLE, bg, seed=7):
    make_card(data["title"], bg)
img = Image.open(bg).convert("RGB").resize((W, H))
grad = Image.new("L", (1, H))
for y in range(H):
    grad.putpixel((0, y), int(190 * max(0.0, (y - H * 0.4) / (H * 0.6))))
img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, grad.resize((W, H)))
draw = ImageDraw.Draw(img)
text = (data.get("thumb_text") or data["title"]).upper()
size = 160
while True:
    try:
        font = ImageFont.truetype(FONT, size)
    except Exception:
        font = ImageFont.load_default()
    lines = textwrap.wrap(text, 12)[:3]
    widest = max(draw.textlength(l, font=font) for l in lines)
    if size <= 60 or (widest < W - 100 and len(lines) * (size + 12) < H * 0.6):
        break
    size -= 8
y = H - len(lines) * (size + 12) - 30
for line in lines:
    w = draw.textlength(line, font=font)
    draw.text(((W - w) / 2, y), line, font=font, fill=(255, 214, 0),
              stroke_width=max(6, size // 12), stroke_fill=(0, 0, 0))
    y += size + 12
img.save("build/thumbnail.jpg", quality=92)
print("DONE")
