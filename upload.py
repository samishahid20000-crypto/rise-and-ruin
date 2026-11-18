import os, sys, json, time, requests

CID = os.environ.get("YT_CLIENT_ID")
SEC = os.environ.get("YT_CLIENT_SECRET")
RT = os.environ.get("YT_REFRESH_TOKEN")
if not (CID and SEC and RT):
    print("YouTube secrets missing - skipping upload")
    sys.exit(0)

B = "build"
PRIVACY = os.environ.get("PRIVACY", "public")


def token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CID, "client_secret": SEC,
        "refresh_token": RT, "grant_type": "refresh_token"})
    r.raise_for_status()
    return r.json()["access_token"]


def rd(name):
    p = os.path.join(B, name)
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    return ""


def clean(s):
    return s.replace("<", "").replace(">", "")


title = clean(rd("release_title.txt"))[:100] or "Rise & Ruin"
meta = rd("metadata.txt")
tags = []
for line in meta.splitlines():
    if line.lower().startswith("tags"):
        tags = [t.strip().lstrip("#") for t in line.split(":", 1)[-1].split(",") if t.strip()]
desc = clean(meta)[:4900]
if os.environ.get("MODE") == "short" and "#shorts" not in desc.lower():
    desc += "\n\n#Shorts"

keep, total = [], 0
for t in tags:
    if total + len(t) + 1 > 450:
        break
    keep.append(t)
    total += len(t) + 1

video = os.path.join(B, "video.mp4")
size = os.path.getsize(video)
body = {
    "snippet": {"title": title, "description": desc, "tags": keep, "categoryId": "27"},
    "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False},
}
r = requests.post(
    "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
    headers={"Authorization": "Bearer " + token(),
             "Content-Type": "application/json; charset=UTF-8",
             "X-Upload-Content-Length": str(size),
             "X-Upload-Content-Type": "video/mp4"},
    data=json.dumps(body))
if r.status_code != 200:
    print("init failed", r.status_code, r.text[:500])
    sys.exit(1)
url = r.headers["Location"]

CH = 8 * 1024 * 1024
pos = 0
last = None
with open(video, "rb") as f:
    while pos < size:
        chunk = f.read(CH)
        end = pos + len(chunk) - 1
        for attempt in range(6):
            try:
                last = requests.put(url, data=chunk, timeout=300, headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": "bytes %d-%d/%d" % (pos, end, size)})
                if last.status_code in (200, 201, 308):
                    break
                print("retry", last.status_code)
            except requests.RequestException as e:
                print("retry", e)
            time.sleep(5 * (attempt + 1))
        else:
            sys.exit("upload failed")
        pos = end + 1

vid = last.json()["id"]
print("Uploaded: https://youtu.be/" + vid)

try:
    tp = os.path.join(B, "thumbnail.jpg")
    if os.path.exists(tp):
        t = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=" + vid,
            headers={"Authorization": "Bearer " + token(), "Content-Type": "image/jpeg"},
            data=open(tp, "rb").read())
        print("thumbnail status", t.status_code)
except Exception as e:
    print("thumbnail skipped", e)
