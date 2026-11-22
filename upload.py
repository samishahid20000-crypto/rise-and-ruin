import os, json, re, time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests

MODE = (os.environ.get("MODE") or "long").strip().lower()
SHORT = MODE == "short"
ET = ZoneInfo("America/New_York")
# (weekday 0=Mon .. 6=Sun, hour, minute) in US Eastern time
SLOTS = {"long": [(2, 14, 0), (6, 10, 0)],
         "short": [(0, 19, 0), (1, 19, 0), (3, 19, 0), (4, 19, 0), (5, 15, 0)]}
VIDEO, THUMB, META, STATE = "build/video.mp4", "build/thumbnail.jpg", "build/metadata.txt", "output/schedule.json"


def parse_meta(text):
    heads = {"TITLE OPTIONS": "titles", "DESCRIPTION": "desc", "CHAPTERS": "chapters", "TAGS": "tags",
             "PINNED COMMENT": "pinned"}
    out, key = {}, None
    for line in text.splitlines():
        s = line.strip()
        if s in heads:
            key = heads[s]
            out[key] = []
        elif s.startswith("VERIFY BEFORE UPLOAD"):
            key = "verify"
            out[key] = []
        elif key and s:
            out[key].append(s)
    return out


def build_fields(meta):
    titles = [re.sub(r"^\d+\.\s*", "", t) for t in meta.get("titles", [])]
    title = (titles[0] if titles else "Rise and Ruin")[:100]
    desc = [l for l in meta.get("desc", []) if not l.startswith("(add your own")]
    text = "\n".join(desc)
    if meta.get("chapters") and not SHORT:
        text += "\n\nChapters\n" + "\n".join(meta["chapters"])
    if SHORT and "#shorts" not in text.lower():
        text += "\n\n#Shorts"
    tags, total = [], 0
    for t in ", ".join(meta.get("tags", [])).split(","):
        t = t.strip()
        if t and total + len(t) + 1 <= 450:
            tags.append(t)
            total += len(t) + 1
    return title, text[:4900], tags


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def next_slot(now=None):
    state = load_state()
    now = now or datetime.now(timezone.utc)
    taken = []
    for x in state.get(MODE, []):
        try:
            taken.append(datetime.fromisoformat(x))
        except Exception:
            pass
    start = max([now + timedelta(hours=2)] + taken)
    day0 = start.astimezone(ET).date()
    for i in range(0, 200):
        d = day0 + timedelta(days=i)
        for wd, h, mi in sorted(SLOTS[MODE], key=lambda z: z[1]):
            if d.weekday() == wd:
                dt = datetime(d.year, d.month, d.day, h, mi, tzinfo=ET).astimezone(timezone.utc)
                if dt > start:
                    return dt
    return start + timedelta(days=1)


def save_slot(dt):
    state = load_state()
    state.setdefault(MODE, []).append(dt.isoformat())
    state[MODE] = state[MODE][-60:]
    os.makedirs("output", exist_ok=True)
    json.dump(state, open(STATE, "w"), indent=1)


def token():
    r = requests.post("https://oauth2.googleapis.com/token", timeout=60, data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"})
    r.raise_for_status()
    return r.json()["access_token"]


def start_session(tok, body, size):
    return requests.post("https://www.googleapis.com/upload/youtube/v3/videos", timeout=120,
                         params={"uploadType": "resumable", "part": "snippet,status"},
                         headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8",
                                  "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"},
                         data=json.dumps(body))


def send(url, path):
    size = os.path.getsize(path)
    sent = 0
    for attempt in range(6):
        try:
            with open(path, "rb") as f:
                f.seek(sent)
                h = {"Content-Type": "video/mp4", "Content-Length": str(size - sent)}
                if sent:
                    h["Content-Range"] = f"bytes {sent}-{size - 1}/{size}"
                r = requests.put(url, data=f, headers=h, timeout=3600)
            if r.status_code in (200, 201):
                return r.json()
            print("upload status", r.status_code, r.text[:300])
        except requests.RequestException as e:
            print("upload error", e)
        try:
            q = requests.put(url, headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"}, timeout=120)
            if q.status_code in (200, 201):
                return q.json()
            if q.status_code == 308 and q.headers.get("Range"):
                sent = int(q.headers["Range"].split("-")[1]) + 1
            else:
                sent = 0
        except requests.RequestException:
            pass
        time.sleep(10)
    raise SystemExit("upload failed")


def main():
    meta = parse_meta(open(META).read())
    title, desc, tags = build_fields(meta)
    when = next_slot()
    body = {"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "27",
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
                       "publishAt": when.strftime("%Y-%m-%dT%H:%M:%S.000Z")}}
    tok = token()
    size = os.path.getsize(VIDEO)
    r = start_session(tok, body, size)
    scheduled = True
    if r.status_code != 200:
        print("schedule rejected", r.status_code, r.text[:300], "- uploading as private instead")
        del body["status"]["publishAt"]
        scheduled = False
        r = start_session(tok, body, size)
    if r.status_code != 200:
        print(r.status_code, r.text[:500])
        raise SystemExit("could not start upload")
    video = send(r.headers["Location"], VIDEO)
    vid = video.get("id")
    print("uploaded", vid, title)
    if scheduled:
        save_slot(when)
        print("SCHEDULED for", when.astimezone(ET).strftime("%A %Y-%m-%d %I:%M %p Eastern"))
    if vid and os.path.exists(THUMB):
        try:
            t = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set", timeout=300,
                              params={"videoId": vid, "uploadType": "media"},
                              headers={"Authorization": "Bearer " + token(), "Content-Type": "image/jpeg"},
                              data=open(THUMB, "rb").read())
            print("thumbnail", t.status_code)
        except Exception as e:
            print("thumbnail error", e)


if __name__ == "__main__":
    main()
        
