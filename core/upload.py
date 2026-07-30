#!/usr/bin/env python3
"""POST assets to Figma MCP upload URLs; write key->imageHash map.

Usage: upload.py manifest.json urls.json out_assets.json
  manifest.json: {"key": "/abs/path/file.png", ...}  (ordered)
  urls.json: ["https://...submit?...", ...]  (same count, from upload_assets MCP call)
"""
import json, subprocess, sys

manifest = json.load(open(sys.argv[1]))
urls = json.load(open(sys.argv[2]))
keys = list(manifest)
assert len(keys) == len(urls), f"{len(keys)} assets vs {len(urls)} urls"
out = {}
for key, url in zip(keys, urls):
    r = subprocess.run(["curl", "-s", "-X", "POST", "-F", f"file=@{manifest[key]}", url],
                       capture_output=True, text=True)
    resp = json.loads(r.stdout)
    if not resp.get("success"):
        sys.exit(f"upload failed for {key}: {r.stdout}")
    out[key] = resp["imageHash"]
    print(f"{key} -> {resp['imageHash'][:12]}")
json.dump(out, open(sys.argv[3], "w"), indent=1)
print(f"wrote {sys.argv[3]} ({len(out)} assets)")
