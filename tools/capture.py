#!/usr/bin/env python3
"""Seeded-simulator capture harness (macOS, simctl).

Boots (or creates) one simulator per device in the project config, installs
the app, injects an identical seed save into the path the app's persistence
code actually uses, grants permissions, launches, screenshots.

usage:
  capture.py --config projects/<app>/config.json --app <Build.app> \
             --seed <game_state.json> --state home --out captures/ [--sizes 40,46]

config.json (see projects/example/config.example.json):
  bundleId, savePath (relative to the app data container),
  permissions: ["location", ...],
  devices: { "40": {"udid": "...", "deviceType": "...", "runtime": "..."}, ... }

Sims are cattle: if a udid is missing or won't boot, the device is recreated
from deviceType+runtime and the new udid is written back to the config.
"""
import argparse
import json
import subprocess
import sys
import time


def run(*cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def ensure_booted(dev, cfg_path, cfg, key):
    udid = dev.get("udid")
    if udid:
        r = subprocess.run(["xcrun", "simctl", "boot", udid],
                           capture_output=True, text=True)
        if r.returncode == 0 or "Booted" in r.stderr:
            run("xcrun", "simctl", "bootstatus", udid, check=False)
            return udid
        print(f"  [{key}] dead sim {udid}, recreating", file=sys.stderr)
    udid = run("xcrun", "simctl", "create", f"vibe2fig-{key}",
               dev["deviceType"], dev["runtime"])
    dev["udid"] = udid
    json.dump(cfg, open(cfg_path, "w"), indent=1)  # write back: udids rot
    run("xcrun", "simctl", "boot", udid, check=False)
    run("xcrun", "simctl", "bootstatus", udid, check=False)
    return udid


def capture(udid, app, bid, seed, save_path, perms, shot):
    run("xcrun", "simctl", "install", udid, app)
    for p in perms:
        run("xcrun", "simctl", "privacy", udid, "grant", p, bid, check=False)
    # first launch creates the data container
    run("xcrun", "simctl", "launch", udid, bid, check=False)
    time.sleep(3)
    run("xcrun", "simctl", "terminate", udid, bid, check=False)
    container = run("xcrun", "simctl", "get_app_container", udid, bid, "data")
    if not container:
        raise RuntimeError("no data container")
    dest = f"{container}/{save_path}"
    run("mkdir", "-p", dest.rsplit("/", 1)[0])
    run("cp", seed, dest)
    run("xcrun", "simctl", "launch", udid, bid, check=False)
    time.sleep(8)
    run("xcrun", "simctl", "io", udid, "screenshot", shot)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--app", required=True)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--state", required=True, help="label for output files")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sizes", help="comma list; default all devices")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    sizes = a.sizes.split(",") if a.sizes else list(cfg["devices"])
    run("mkdir", "-p", a.out)
    for key in sizes:
        dev = cfg["devices"][key]
        udid = ensure_booted(dev, a.config, cfg, key)
        shot = f"{a.out}/{a.state}_{key}.png"
        capture(udid, a.app, cfg["bundleId"], a.seed, cfg["savePath"],
                cfg.get("permissions", []), shot)
        print(f"  [{key}] {shot}")


if __name__ == "__main__":
    main()
