import os, json, math, time, asyncio, subprocess, textwrap, re
import requests
from PIL import Image
import stickman as S

MODE = (os.environ.get("MODE") or "long").strip().lower()
MINUTES = float(os.environ.get("MINUTES") or 13)
TOPIC_ENV = (os.environ.get("TOPIC") or "").strip()
VERTICAL = MODE == "short"
W, H = (720, 1280) if VERTICAL else (1280, 720)
FPS, SEG, WPM = 30, 4.9, 140
VOICE, RATE = "en-US-GuyNeural", "-12%"
MODELS = ["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
RULES = ("Rules: use only well-documented facts. If you are not sure about a number or date, leave it out or say 'around'. "
         "Never invent quotes. Do not accuse real people of crimes unless it was proven in court or is widely documented. "
         "Simple spoken English, short sentences, no jargon, no stage directions.")


# ---------------- helpers ----------------
def ask(prompt, as_json=True):
    for attempt in range(4):
        for m in MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            body = {"contents": [{"parts": [{"text": prompt}]}]}
            if as_json:
                body["generationConfig"] = {"responseMimeType": "application/json"}
            try:
                r = requests.post(url, params={"key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=180)
            except requests.RequestException as e:
                print(m, "network error", e)
                continue
            if r.status_code == 200:
                try:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    time.sleep(3)
                    return json.loads(text) if as_json else text.strip()
                except Exception as e:
                    print(m, "bad reply", e)
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
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


def clean(text):
    text = re.sub(r"[*_`]", "", str(text))
    text = re.sub(r"^#+\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def stamp(sec):
    sec = int(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pick_topic():
    if TOPIC_ENV:
        return TOPIC_ENV
    topics = json.load(open("topics.json"))
    used = json.load(open("output/used.json")) if os.path.exists("output/used.json") else []
    for t in topics:
        if f"{MODE}:{t}" not in used:
            return t
    raise SystemExit("all topics are used")


def mark_used(topic):
    used = json.load(open("output/used.json")) if os.path.exists("output/used.json") else []
    if f"{MODE}:{topic}" not in used:
        used.append(f"{MODE}:{topic}")
    json.dump(used, open("output/used.json", "w"), indent=1)


# ---------------- script ----------------
def plan_long(topic, words):
    n = max(8, min(24, round(words / 250)))
    p = f"""You are the head writer of the YouTube channel Rise & Ruin: stick-figure documentaries about how companies and empires rose and collapsed. Audience: adults 20-40 in the USA, UK, Canada and Australia. Topic: the rise and ruin of {topic}.
Plan one video of about {words} spoken words with exactly {n} chapters in this order: Hook, Context, The Rise (several chapters, act rise), The Crack (one chapter: the single decision or moment that started the collapse, act crack), The Ruin (several chapters, act ruin), The Lesson (act neutral).
Return ONLY JSON with keys:
title_options: 3 strong YouTube titles, each under 60 characters, using the patterns contrast, mistake or question;
description: 2 sentence summary for the description;
tags: 12 tags;
chapters: list of exactly {n} objects with name (short), act (rise, crack, ruin or neutral), summary (2 sentences on what happens), words (integer, all together about {words});
thumb_text: 2 to 4 words in capital letters;
thumb_pose: one of {S.POSE_NAMES};
thumb_props: 1 or 2 items from {S.PROP_NAMES};
verify: list of the 8 most important facts, dates or numbers a human should double check.
{RULES}"""
    plan = ask(p)
    if isinstance(plan, list) and plan:
        plan = plan[0]
    chs = plan.get("chapters") or []
    if len(chs) < 4:
        raise SystemExit("bad plan")
    return plan


def write_chapter(topic, plan, i, prev_tail):
    chs = plan["chapters"]
    ch = chs[i]
    outline = "\n".join(f"{j + 1}. {c.get('name')}: {c.get('summary')}" for j, c in enumerate(chs))
    if i == 0:
        extra = ("This is the HOOK: open with the shocking outcome, the stakes and a promise. Add one open loop "
                 "(the real mistake was not what people think) that gets answered later. Do not say welcome or subscribe.")
    elif i == 1:
        extra = "Briefly say who they were. End this chapter with one natural sentence inviting viewers to subscribe because a new collapse is told every week."
    elif i == len(chs) - 1:
        extra = "Give three lessons and what they should have done. Then ask which company viewers want next in the comments and tease the next story."
    else:
        extra = "End the chapter with one short re-hook sentence that makes the next chapter feel necessary."
    p = f"""Write the spoken narration for chapter {i + 1} of {len(chs)} ("{ch.get('name')}") of a Rise & Ruin documentary about {topic}.
Full outline:
{outline}
This chapter must cover: {ch.get('summary')}
Length: about {ch.get('words', 250)} words.
{extra}
The previous chapter ended with: "{prev_tail}"
Continue naturally and do not repeat earlier facts.
{RULES}
Return ONLY the narration text, plain, with no title and no headings."""
    return clean(ask(p, as_json=False))


def plan_short(topic):
    p = f"""You write YouTube Shorts for the channel Rise & Ruin (stick-figure stories about how companies and empires rose and collapsed). Topic: the rise and ruin of {topic}.
Write a script of about 120 spoken words (50 seconds). Line 1 is a shocking hook (outcome plus stakes). Then 4 fast beats: the rise, the single mistake, the ruin, a one-line lesson. The last line is: Follow for the next collapse.
Return ONLY JSON with keys: title_options (3 titles under 60 characters), description (2 lines ending with #Shorts), tags (10 tags), script, verify (list of the 5 key facts or numbers to double check).
{RULES}"""
    plan = ask(p)
    if isinstance(plan, list) and plan:
        plan = plan[0]
    return plan


# ---------------- voice ----------------
async def tts(text, path):
    import edge_tts
    try:
        comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    except TypeError:
        comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    marks = []
    with open(path, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] in ("WordBoundary", "SentenceBoundary"):
                marks.append((ch["offset"] / 1e7, ch["duration"] / 1e7, ch["text"]))
    return marks


def make_voice(i, text):
    mp3 = f"build/v{i:02d}.mp3"
    wav = f"build/v{i:02d}.wav"
    for attempt in range(3):
        try:
            marks = asyncio.run(tts(text, mp3))
            if os.path.getsize(mp3) > 2000:
                break
        except Exception as e:
            print("tts error", e)
            time.sleep(5)
    else:
        raise SystemExit("voice failed")
    run(["ffmpeg", "-y", "-i", mp3, "-ar", "24000", "-ac", "1", wav])
    return wav, marks


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
    else:
        n = max(1, math.ceil(total / SEG))
        for i in range(n):
            a, b = round(i * len(words) / n), round((i + 1) * len(words) / n)
            segs.append((total * i / n, total * (i + 1) / n, " ".join(words[a:b])))
    final = []
    for a, b, t in segs:
        k = max(1, math.ceil((b - a) / SEG))
        for j in range(k):
            final.append((a + (b - a) * j / k, a + (b - a) * (j + 1) / k, t))
    return final


# ---------------- scenes ----------------
def fallback_scene(text, act):
    words = [w for w in re.findall(r"[A-Za-z0-9$%']+", text)]
    cap = " ".join(words[:4])
    return {"act": act, "pose": "stand", "props": ["label:" + (words[-1] if words else "?")], "caption": cap}


def sanitize(sc, text, act):
    if not isinstance(sc, dict):
        return fallback_scene(text, act)
    out = {}
    out["act"] = sc.get("act") if sc.get("act") in S.BG else act
    out["pose"] = sc.get("pose") if sc.get("pose") in S.POSE_NAMES else "stand"
    props = sc.get("props") or []
    if isinstance(props, str):
        props = [props]
    props = [re.sub(r"\s+", " ", str(p)).strip()[:30] for p in props if str(p).strip()]
    out["props"] = props[:2 if VERTICAL else 3] or ["label:" + clean(text).split(" ")[0]]
    out["caption"] = clean(sc.get("caption", ""))[:40] or " ".join(clean(text).split(" ")[:4])
    return out


def get_scenes(items):
    out = []
    for s in range(0, len(items), 25):
        part = items[s:s + 25]
        listing = "\n".join(f"{i + 1}. [{act}] {text}" for i, (text, act) in enumerate(part))
        p = f"""You design stick-figure scenes for a documentary. For each numbered narration line decide what the viewer SEES while it is spoken. The scene must show the main thing the line talks about.
Return ONLY a JSON list of exactly {len(part)} objects with keys:
act: rise, crack, ruin or neutral (use the hint in brackets unless the line clearly says otherwise);
pose: one of {S.POSE_NAMES} (the stick man's mood: cheer for success, sad or panic for failure, think or shrug for doubt, point for explaining, run for hurry);
props: 1 to {2 if VERTICAL else 3} items. Use names from {S.PROP_NAMES}. If the line is about something not in the list, use "label:" plus one or two words (for example "label:IPHONE" or "label:LAYOFFS"). Phone lines show phone or smartphone, towers show tower, money shows money or coins, falling shows chart_down or arrow_down, growth shows chart_up or arrow_up, people show crowd, secrets or deals show contract or lock;
caption: the punchy key phrase of the line in 2 to 4 words, include a number if the line has one.
Do not repeat the same props and pose in two lines in a row.

{listing}"""
        res = ask(p)
        if not isinstance(res, list):
            res = []
        for i, (text, act) in enumerate(part):
            sc = res[i] if i < len(res) else None
            out.append(sanitize(sc, text, act))
    return out


def motion(i, frames):
    tail = f"d={frames}:s={W}x{H}:fps={FPS}"
    m = i % 3
    if m == 0:
        z = f"zoompan=z='min(zoom+0.0006,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':{tail}"
    elif m == 1:
        z = f"zoompan=z='max(1.12-0.0006*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':{tail}"
    else:
        z = f"zoompan=z=1.1:x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':{tail}"
    return z


# ---------------- main ----------------
def main():
    os.makedirs("output", exist_ok=True)
    os.makedirs("build/clips", exist_ok=True)
    topic = pick_topic()
    print("MODE", MODE, "TOPIC", topic)

    chapters = []
    if VERTICAL:
        plan = plan_short(topic)
        chapters = [{"name": "Short", "act": "neutral", "text": clean(plan["script"])}]
    else:
        words_total = int(MINUTES * WPM)
        plan = plan_long(topic, words_total)
        prev = ""
        for i, ch in enumerate(plan["chapters"]):
            text = write_chapter(topic, plan, i, prev)
            prev = " ".join(text.split(" ")[-25:])
            act = ch.get("act") if ch.get("act") in S.BG else "neutral"
            chapters.append({"name": clean(ch.get("name", f"Part {i + 1}")), "act": act, "text": text})
            print("chapter", i + 1, len(text.split()), "words")

    # voice per chapter, exact timing
    segs, wavs, starts, t0 = [], [], [], 0.0
    for i, ch in enumerate(chapters):
        wav, marks = make_voice(i, ch["text"])
        dur = duration(wav)
        wavs.append(wav)
        starts.append(t0)
        for a, b, text in build_segments(marks, ch["text"].split(), dur):
            if VERTICAL:
                pos = (t0 + a) / max(dur, 1)
                act = "neutral" if pos < 0.12 else "rise" if pos < 0.35 else "crack" if pos < 0.5 else "ruin" if pos < 0.9 else "neutral"
            else:
                act = ch["act"]
            segs.append((t0 + a, t0 + b, text, act))
        t0 += dur
    total = t0
    print("voice seconds", round(total), "visuals", len(segs))

    with open("build/wavs.txt", "w") as f:
        for w in wavs:
            f.write(f"file '{os.path.abspath(w)}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "build/wavs.txt", "-c", "copy", "build/voice.wav"])

    scenes = get_scenes([(t, act) for _, _, t, act in segs])

    # visuals
    S.SS = 1
    clips, prev_frames = [], 0
    for i, ((a, b, text, act), sc) in enumerate(zip(segs, scenes)):
        end_frames = round(b * FPS)
        frames = max(2, end_frames - prev_frames)
        prev_frames = end_frames
        png = f"build/clips/s{i:03d}.png"
        out = f"build/clips/c{i:03d}.mp4"
        S.render_scene(sc, W * 2, H * 2, path=png)
        run(["ffmpeg", "-y", "-i", png, "-vf", motion(i, frames) + ",format=yuv420p", "-frames:v", str(frames),
             "-an", "-c:v", "libx264", "-preset", "veryfast", out])
        os.remove(png)
        clips.append(out)
        if i % 10 == 0:
            print("visual", i, "/", len(segs), sc["caption"])

    with open("build/list.txt", "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "build/list.txt", "-c", "copy", "build/joined.mp4"])
    run(["ffmpeg", "-y", "-i", "build/joined.mp4", "-i", "build/voice.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "build/video.mp4"])

    # thumbnail (stick man + bold text)
    tprops = plan.get("thumb_props") if isinstance(plan.get("thumb_props"), list) else []
    tsc = sanitize({"act": "ruin", "pose": plan.get("thumb_pose"), "props": tprops[:2] or ["crown_crack"],
                    "caption": plan.get("thumb_text") or topic}, topic, "ruin")
    S.SS = 2
    S.render_scene(tsc, 1280, 720, path="build/thumbnail.jpg", style="thumb")

    # metadata
    titles = plan.get("title_options") or [f"The Rise and Ruin of {topic}"]
    lines = ["TITLE OPTIONS"] + [f"{i + 1}. {clean(t)}" for i, t in enumerate(titles)]
    lines += ["", "DESCRIPTION", clean(plan.get("description", ""))]
    if not VERTICAL:
        lines += ["", "(add your own 2-3 real sources here before uploading)", "", "CHAPTERS"]
        for st, ch in zip(starts, chapters):
            lines.append(f"{stamp(st)} {ch['name']}")
    lines += ["", "TAGS", ", ".join(clean(t) for t in (plan.get("tags") or []))]
    lines += ["", "PINNED COMMENT", "Which company should we cover next? Tell us below.",
              "", "VERIFY BEFORE UPLOAD (facts and numbers used)"]
    lines += [f"- {clean(v)}" for v in (plan.get("verify") or [])]
    meta = "\n".join(lines)
    open("build/metadata.txt", "w").write(meta)
    open("build/release_notes.md", "w").write(meta)
    open("build/release_title.txt", "w").write(f"{'SHORT' if VERTICAL else 'LONG'}: {topic}")
    json.dump({"topic": topic, "mode": MODE, "chapters": [c["name"] for c in chapters]}, open("output/last.json", "w"))
    mark_used(topic)
    print("DONE", round(total), "seconds")


if __name__ == "__main__":
    main()
