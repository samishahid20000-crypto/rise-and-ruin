import subprocess


def install(g=None):
    return None


def clip(S, sc, W, H, frames, FPS, out, png):
    try:
        S.render_scene(sc, W, H, path=png)
    except TypeError:
        S.render_scene(sc, W, H, png)
    frames = max(2, int(frames))
    zoom = ("zoompan=z='min(1+0.0008*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            ":d=%d:s=%dx%d:fps=%d" % (frames, W, H, FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", png,
           "-vf", zoom + ",format=yuv420p",
           "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-r", str(FPS), out]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-800:])
        raise SystemExit("clip failed")
