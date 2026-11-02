"""Find out which Gemini model answers fast for your API key.

Run (Windows CMD):
    set GEMINI_API_KEY=your-key
    python tools/check_gemini.py
Nothing is saved; the key is only read from the environment.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

KEY = os.environ.get("GEMINI_API_KEY")
if not KEY:
    sys.exit("Set GEMINI_API_KEY first:  set GEMINI_API_KEY=your-key")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def get(url):
    req = urllib.request.Request(url, headers={"x-goog-api-key": KEY})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def ask(model):
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": 'Reply with exactly this JSON: {"ok": true}'}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 200, "responseMimeType": "application/json"},
    }).encode("utf-8")
    req = urllib.request.Request(
        "%s/%s:generateContent" % (BASE, model), data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0].get("text", "")[:40]
        return "%.1fs  OK  %s" % (time.time() - start, text.strip())
    except urllib.error.HTTPError as e:
        return "%.1fs  HTTP %d  %s" % (time.time() - start, e.code, e.read().decode("utf-8", "ignore")[:90].replace("\n", " "))
    except Exception as e:
        return "%.1fs  FAILED  %r" % (time.time() - start, e)


try:
    models = [m["name"].split("/")[-1] for m in get(BASE + "?pageSize=200").get("models", [])
              if "generateContent" in m.get("supportedGenerationMethods", [])]
except Exception as e:
    sys.exit("Could not list models (%r). Check the key and your internet." % e)

fast = [m for m in models if "flash" in m and "preview" not in m and "image" not in m and "tts" not in m][:6]
current = os.environ.get("GEMINI_MODEL")
tests = ([current] if current else []) + [m for m in fast if m != current]
print("Models that can generate text (first 15):", ", ".join(models[:15]))
print()
for m in tests:
    print("%-34s %s" % (m, ask(m)))
print("\nPick one that shows OK and the smallest time, then set  GEMINI_MODEL = \"<name>\"  in secrets.")