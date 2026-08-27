"""
FahmyLoader Extractor Server — free yt-dlp based video link resolver.
Endpoint: GET/POST /api?url=VIDEO_URL
Returns JSON: {"url": "<direct media url>", "title": "..."} or {"error": "..."}
Deploy free on Render.com (Python 3.11).
"""
import json
import re
import subprocess
import tempfile
import os
from flask import Flask, request, jsonify

app = Flask(__name__)


def clean_url(url):
    # strip tracking junk
    return url.strip()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "FahmyLoader Extractor",
        "usage": "/api?url=https://...",
        "status": "ok"
    })


@app.route("/api", methods=["GET", "POST"])
def api():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        url = data.get("url") or data.get("link") or ""
        if not url and "url" in request.form:
            url = request.form["url"]
    else:
        url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "missing url parameter"}), 400

    url = clean_url(url)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            # ask yt-dlp for the best direct mp4 url + title, no download
            cmd = [
                "yt-dlp",
                "--no-warnings",
                "--dump-json",
                "--no-playlist",
                "-f", "best[ext=mp4]/best",
                url,
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=tmp,
            )
            out = proc.stdout.strip()
            if not out:
                err = proc.stderr.strip().splitlines()
                msg = err[-1] if err else "extraction failed"
                return jsonify({"error": msg[:300]}), 422

            # yt-dlp --dump-json prints one JSON object (or multiple for playlists)
            info = json.loads(out.splitlines()[0])
            direct = info.get("url") or info.get("webpage_url")
            title = info.get("title", "video")
            # prefer a direct file url
            if ".googlevideo.com" in direct or direct.endswith((".mp4", ".webm", ".m3u8")):
                return jsonify({"url": direct, "title": title})
            # fallback: try to get the http url field
            for f in info.get("formats", []):
                u = f.get("url", "")
                if u.endswith((".mp4", ".webm")):
                    return jsonify({"url": u, "title": title})
            return jsonify({"url": direct, "title": title})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "extraction timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
