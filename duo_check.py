import json, os, urllib.parse, urllib.request

PARTS = ["MK1E4LL/A", "MK1F4LL/A"]
LABELS = {"MK1E4LL/A": "256GB Star White", "MK1F4LL/A": "256GB Night Sky"}
CPPART = "UNLOCKED/US"
LOCATION = "47404"
ALLOWED = ["Fashion Mall at Keystone", "Oxmoor"]
TOPIC = os.environ["NTFY_TOPIC"]
BASE = "https://www.apple.com/us-edu/shop/buy-iphone/iphone-duo/7.6-inch-display-256gb-"
URLS = {"256GB Night Sky": BASE + "night-sky-unlocked"}
DEFAULT_URL = BASE + "star-white-unlocked"
STATE = "state.json"


def notify(title, message, click=None):
    headers = {"Title": title, "Priority": "urgent", "Tags": "iphone"}
    if click:
        headers["Click"] = click
    req = urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=message.encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception as e:
        print("notify failed:", e)
        return False


def check(part):
    qs = urllib.parse.urlencode({"fae": "true", "mts.0": "regular", "cppart": CPPART,
                                 "location": LOCATION, "product": part})
    req = urllib.request.Request(
        "https://www.apple.com/us-edu/shop/pickup-message-recommendations?" + qs,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    body = data["body"]
    pm = body.get("PickupMessage") or body.get("pickupMessage") or body.get("content", {}).get("pickupMessage") or {}
    stores = pm.get("stores", [])
    avail = []
    for s in stores:
        pa = s.get("partsAvailability", {})
        info = pa.get(part) or (next(iter(pa.values())) if pa else {})
        if info.get("pickupDisplay") == "available":
            avail.append(s.get("storeName", "Unknown store"))
    return len(stores), avail


def main():
    if os.environ.get("TEST_NOTIFY") == "true":
        print("test notification sent:", notify("Duo cloud test", "GitHub watcher can reach your phone."))
    try:
        with open(STATE) as f:
            old = json.load(f)
    except Exception:
        old = {}
    new = {}
    fails = 0
    for part in PARTS:
        try:
            n, avail = check(part)
        except Exception as e:
            fails += 1
            new[part] = old.get(part, [])
            print("check failed:", part, e)
            continue
        wanted = [s for s in avail if any(a.lower() in s.lower() for a in ALLOWED)]
        kept = []
        for s in wanted:
            if s in old.get(part, []):
                kept.append(s)
            else:
                label = LABELS.get(part, "256GB")
                msg = f"{s}: {label} unlocked ({part}) shows pickup available. Tap to open Apple."
                if notify("iPhone Duo in stock! (cloud)", msg, click=URLS.get(label, DEFAULT_URL)):
                    kept.append(s)
                    print("ALERT sent:", s, part)
        new[part] = kept
        others = [s for s in avail if s not in wanted]
        print(f"checked {part}: {n} stores, {len(avail)} available", ("| not on list: " + ", ".join(others)) if others else "")
    with open(STATE, "w") as f:
        json.dump(new, f, indent=1, sort_keys=True)
    if fails == len(PARTS):
        raise SystemExit("all checks failed")


main()
