import os, json, math, time, asyncio, subprocess, textwrap, requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont

KEY = os.environ["GEMINI_API_KEY"]
PIX = os.environ["PIXABAY_API_KEY"]
TOPIC = "The rise and fall of Nokia"
MODELS = ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
W, H, FPS = 1280, 720, 30
SEG = 4.9  # max seconds per visual
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


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


def pix(url, params):
    for _ in range(3):
        try:
            r = requests.get(url, params=dict(params, key=PIX, safesearch="true"), timeout=30)
        except Exception as e:
            print("pixabay error", e)
            time.sleep(5)
            continue
        time.sleep(0.8)
        if r.status_code == 200:
            return r.json().get("hits", [])
        if r.status_code == 429:
            print("rate limit, waiting")
            time.sleep(40)
            continue
        print("pixabay", r.status_code)
        return []
    return []


def find_media(a, b, used):
    tries = []
    for t in (a, b, a.split()[-1] if a.split() else ""):
        t = t.strip()
        if t and t not in tries:
            tries.append(t)
    for t in tries:
        for hit in pix("https://pixabay.com/api/videos/", {"q": t, "per_page": 20}):
            if hit.get("duration", 0) < 5:
                continue
            v = hit.get("videos", {})
            pick = v.get("medium") or v.get("small")
            if pick and pick.get("url") and pick["url"] not in used:
                return "video", pick["url"]
        for itype in ("illustration", "photo"):
            for hit in pix("https://pixabay.com/api/", {"q": t, "image_type": itype,
                                                          "orientation": "horizontal", "per_page": 20}):
                u = hit.get("largeImageURL")
                if u and u not in used:
                    return "image", u
    return None


def download(url, path):
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


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


def get_queries(texts):
    out = []
    for s in range(0, len(texts), 40):
        part = texts[s:s + 40]
        listing = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(part))
        p = f"""Video topic: {TOPIC}. Below are consecutive narration lines. For each line decide what a viewer should SEE while it is spoken. Give "a": a 2 or 3 word stock-footage or illustration search phrase that directly shows what the line talks about, and "b": a simpler one-word backup. Use generic visuals only, never brand names or people's names. Do not give the same phrase twice in a row. Return ONLY a JSON list of exactly {len(part)} objects with keys a and b, in the same order.

{listing}"""
        res = ask(p)
        if not isinstance(res, list):
            res = []
        items = []
        for x in res[:len(part)]:
            if isinstance(x, dict):
                items.append((str(x.get("a", "")), str(x.get("b", ""))))
            else:
                items.append((str(x), ""))
        while len(items) < len(part):
            items.append(("", ""))
        out += items
    return out


VF = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
ENC = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p"]

prompt = f"""You write scripts for the YouTube channel Rise & Ruin (the rise and fall of famous companies and empires). Audience: USA, UK, Canada, Australia. Topic: {TOPIC}.
Return ONLY JSON with keys: title, description, tags (list of strings), script.
The script is spoken narration of about 600 words, with a strong hook in the first line, no stage directions, original wording."""

data = ask(prompt)
os.makedirs("output", exist_ok=True)
os.makedirs("build/clips", exist_ok=True)
with open("output/video.json", "w") as f:
    json.dump(data, f, indent=2)

words = data["script"].split()
marks = asyncio.run(tts(data["script"], "output/voice.mp3"))
total = duration("output/voice.mp3")
segs = build_segments(marks, words, total)
print("voice seconds", total, "visuals", len(segs))

queries = get_queries([s[2] for s in segs])

used, clips = set(), []
prev_frames = 0
for i, ((a, b, text), (qa, qb)) in enumerate(zip(segs, queries)):
    end_frames = round(b * FPS)
    frames = max(2, end_frames - prev_frames)
    prev_frames = end_frames
    out = f"build/clips/c{i:03d}.mp4"
    found = find_media(qa, qb, used) if (qa or qb) else None
    done = False
    if found:
        kind, url = found
        used.add(url)
        src = f"build/clips/src{i:03d}" + (".mp4" if kind == "video" else ".jpg")
        try:
            download(url, src)
            if kind == "video":
                run(["ffmpeg", "-y", "-i", src, "-frames:v", str(frames), "-vf", VF] + ENC + [out])
            else:
                run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", src,
                     "-frames:v", str(frames), "-vf", VF] + ENC + [out])
            os.remove(src)
            done = True
            print("visual", i, qa, "|", kind)
        except BaseException as e:
            print("visual failed", i, qa, e)
    if not done:
        card = f"build/clips/card{i:03d}.jpg"
        make_card(qa or qb or text[:40], card)
        run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", card,
             "-frames:v", str(frames), "-vf", VF] + ENC + [out])
        print("visual", i, qa, "| text card")
    clips.append(out)

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
    font = ImageFont.truetype(FONT, 90)
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
