import re
from mprops import detect
from mprops2 import EXTRA

BASE = ["building", "phone", "tech", "coin", "chart_up", "chart_down", "gear", "bulb", "trophy", "cross"]
VISUALS = BASE + list(EXTRA) + ["versus"]
GUIDE = """building = company, office, headquarters
phone = mobile phone, calls
tech = technology, chip, software, internet, AI
coin = profit, revenue, money, price
chart_up = growth, rising numbers, market share gained
chart_down = decline, falling sales, losses
gear = factory, production, process, machine
bulb = idea, invention, innovation
trophy = win, number one, success, award
cross = failure, rejection, mistake, banned
clock = time, deadline, waiting, too late
hourglass = time running out
calendar = days, months, years passing
globe = worldwide, global market, expansion abroad
bank = bank, investors, loans, debt, finance
store = shop, retail, customers buying
cart = shopping, sales, orders
truck = delivery, shipping, logistics
plane = airline, travel, flight
newspaper = news, press, headlines, rumors
contract = deal, agreement, law, lawsuit, merger, signed paper
magnifier = investigation, audit, discovery, close look
crown = empire, king, power, dominance
crown_crack = empire starting to crack
lock = secret, patent, blocked, locked, trapped
people = customers, employees, public, crowd, competitors
explosion = scandal, disaster, sudden shocking collapse
question = mystery, why, doubt, unknown
laptop = computers, online work, software work
tv = television, media, advertising, entertainment
fire = crisis, burning cash, heat, danger
moneybag = wealth, billions, savings, fortune
target = goal, strategy, focus, aim
rocket = fast growth, launch, startup, takeoff
book = lesson, history, story, education
camera = photos, film, cameras, media
lightning = speed, energy, sudden change, competition
versus = two things compared (put the two names in labels)"""
FALL = {"rise": ["rocket", "trophy", "chart_up", "globe"], "crack": ["magnifier", "question", "lightning", "people"],
        "ruin": ["chart_down", "explosion", "fire", "cross"], "neutral": ["people", "globe", "book", "clock"]}


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"[*_`#]", "", str(t))).strip()


def pick_visuals(sc, text, act, recent):
    vis = sc.get("visuals") if isinstance(sc, dict) else None
    if isinstance(vis, str):
        vis = [vis]
    vis = [v for v in (vis or []) if v in VISUALS][:2]
    if not vis:
        low = {"narration": text}
        found, _, explicit = detect(low, act)
        vis = found if explicit else []
    if not vis:
        opts = FALL.get(act, FALL["neutral"])
        vis = [opts[sum(map(ord, text)) % len(opts)]]
    # never show the same picture as the line before
    if vis[0] in recent[-2:]:
        if len(vis) > 1 and vis[1] not in recent[-2:]:
            vis = [vis[1], vis[0]]
        else:
            opts = [o for o in FALL.get(act, FALL["neutral"]) + FALL["neutral"] if o not in recent[-2:]]
            if opts:
                vis = vis[:1] + [opts[sum(map(ord, text)) % len(opts)]]
    return vis[:2]


def sanitize(sc, text, act, S, vertical, recent=None):
    recent = recent if recent is not None else []
    sc = sc if isinstance(sc, dict) else {}
    out = {}
    out["act"] = sc.get("act") if sc.get("act") in S.BG else act
    out["pose"] = sc.get("pose") if sc.get("pose") in S.POSE_NAMES else "stand"
    props = sc.get("props") or []
    if isinstance(props, str):
        props = [props]
    props = [re.sub(r"\s+", " ", str(p)).strip()[:30] for p in props if str(p).strip()]
    words = clean(text).split(" ")
    out["props"] = props[:3] or ["label:" + words[0]]
    out["caption"] = clean(sc.get("caption", ""))[:40] or " ".join(words[:4])
    out["visuals"] = pick_visuals(sc, text, out["act"], recent)
    recent.append(out["visuals"][0])
    out["scene"] = "versus" if out["visuals"][0] == "versus" else "generic"
    out["narration"] = clean(text)
    labs = sc.get("labels") or []
    if isinstance(labs, str):
        labs = [labs]
    labs = [clean(x)[:22] for x in labs if str(x).strip()][:3]
    out["labels"] = labs or [out["caption"]]
    return out


def get_scenes(items, ask, S, vertical):
    out, recent = [], []
    for s in range(0, len(items), 25):
        part = items[s:s + 25]
        listing = "\n".join(f"{i + 1}. [{act}] {text}" for i, (text, act) in enumerate(part))
        p = f"""You are the director of a stick-figure documentary. For each numbered narration line choose the pictures the viewer sees while the line is spoken. The picture MUST show what the line is about. Never use stairs or ladders.
Allowed visuals (use only these exact names):
{GUIDE}
Return ONLY a JSON list of exactly {len(part)} objects with keys:
visuals: 1 or 2 names from the list above, in the order the things are spoken in the line (a second one only if the line clearly names a second thing);
act: rise, crack, ruin or neutral (use the hint in brackets unless the line clearly says otherwise);
pose: one of {S.POSE_NAMES} (the stick man's mood: cheer for success, sad or panic for failure, think or shrug for doubt);
caption: the key phrase of the line in 2 to 4 words, include a number if the line has one;
labels: 0 to 3 very short texts (max 3 words each) that name what is shown, for example ["Nokia 2007", "#1 phone maker"] or the two names for versus.
Do not use the same first visual in two lines in a row. Pick the most specific visual for each line.

{listing}"""
        res = ask(p)
        if not isinstance(res, list):
            res = []
        for i, (text, act) in enumerate(part):
            out.append(sanitize(res[i] if i < len(res) else None, text, act, S, vertical, recent))
    return out
  
