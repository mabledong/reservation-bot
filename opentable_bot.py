import os
import json
import re
import smtplib
import httpx
from datetime import datetime, timedelta
from email.mime.text import MIMEText

GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

CARRIER_GATEWAYS = {
    "tmobile": "tmomail.net",
    "att": "txt.att.net",
    "verizon": "vtext.com",
    "sprint": "messaging.sprintpcs.com",
    "cricket": "sms.cricketwireless.net",
    "metro": "mymetropcs.com",
    "boost": "sms.myboostmobile.com",
    "uscellular": "email.uscc.net",
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "restaurants.json")
with open(CONFIG_PATH) as f:
    config = json.load(f)

PARTY_SIZE = config["party_size"]
PHONE_NUMBER = config.get("phone_number")
PHONE_CARRIER = config.get("phone_carrier")
RESTAURANTS = [r for r in config["restaurants"] if r["platform"] == "opentable" and r.get("active", True)]

_venue_cache = {}


def get_sms_address():
    if PHONE_NUMBER and PHONE_CARRIER:
        gateway = CARRIER_GATEWAYS.get(PHONE_CARRIER.lower())
        if gateway:
            return f"{PHONE_NUMBER}@{gateway}"
    return None


def find_opentable_venue(name):
    if name in _venue_cache:
        return _venue_cache[name]

    try:
        resp = httpx.get(
            "https://www.opentable.com/s/",
            params={"term": name, "covers": str(PARTY_SIZE)},
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
            timeout=15,
        )
        if resp.status_code == 200:
            rid_match = re.search(r'"rid"\s*:\s*"?(\d+)"?', resp.text)
            slug_match = re.search(r'"slug"\s*:\s*"([a-z0-9][a-z0-9\-]+)"', resp.text)
            if rid_match:
                rid = rid_match.group(1)
                url = (
                    f"https://www.opentable.com/r/{slug_match.group(1)}"
                    if slug_match
                    else None
                )
                result = (rid, url)
                _venue_cache[name] = result
                return result
        else:
            print(f"  OpenTable search returned {resp.status_code} for '{name}'")
    except Exception as e:
        print(f"  OpenTable lookup error for '{name}': {e}")

    print(f"  Could not auto-find '{name}' - add 'rid' and 'url' fields to restaurants.json")
    return None, None


def time_slots_24h(time_start, time_end):
    start = datetime.strptime(time_start, "%H:%M")
    end = datetime.strptime(time_end, "%H:%M")
    slots = []
    t = start
    while t <= end:
        slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=30)
    return slots


def send_notifications(restaurant, date, available_times, booking_url):
    times_str = ", ".join(available_times)
    subject = f"{restaurant} has availability for {date}!"
    body = f"""
A table for {PARTY_SIZE} is available at {restaurant} on {date}!

Available times: {times_str}

Click here to book now:
{booking_url}

Act fast - these go quickly!
    """

    recipients = [GMAIL_EMAIL]
    sms_address = get_sms_address()
    if sms_address:
        recipients.append(sms_address)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            for recipient in recipients:
                msg = MIMEText(body)
                msg["Subject"] = subject
                msg["From"] = GMAIL_EMAIL
                msg["To"] = recipient
                server.sendmail(GMAIL_EMAIL, recipient, msg.as_string())
        print(f"  Notifications sent!")
        if sms_address:
            print(f"  SMS sent to {PHONE_NUMBER}")
    except Exception as e:
        print(f"  Notification failed: {e}")


def check_availability(restaurant, date):
    name = restaurant["name"]
    time_start = restaurant["time_start"]
    time_end = restaurant["time_end"]
    preferred_times = time_slots_24h(time_start, time_end)

    rid = restaurant.get("rid")
    url = restaurant.get("url")
    if not rid:
        rid, discovered_url = find_opentable_venue(name)
        if not rid:
            return False
        if not url:
            url = discovered_url

    print(f"\nChecking {name} for {date}...")

    try:
        response = httpx.get(
            "https://www.opentable.com/dapi/fe/gql",
            params={
                "operationName": "RestaurantsAvailability",
                "variables": json.dumps({
                    "restaurantIds": [int(rid)],
                    "date": date,
                    "partySize": PARTY_SIZE,
                    "startTime": time_start,
                    "endTime": time_end,
                }),
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            slots = []
            try:
                timeslots = data["data"]["availability"][0]["timeslots"]
                for slot in timeslots:
                    time = slot.get("time", "")
                    if any(t in time for t in preferred_times):
                        slots.append(time)
            except Exception:
                pass

            if slots:
                print(f"  Found availability: {slots}")
                send_notifications(name, date, slots, url or "https://www.opentable.com")
                return True
            else:
                print(f"  No availability found for {name} on {date}")
                return False
        else:
            print(f"  API returned {response.status_code}")
            return False

    except Exception as e:
        print(f"  Error checking {name}: {e}")
        return False


def main():
    print("Starting OpenTable availability checker...")
    print(f"Checking {len(RESTAURANTS)} restaurants\n")

    for restaurant in RESTAURANTS:
        for date in restaurant["dates"]:
            check_availability(restaurant, date)

    print("\nDone!")


if __name__ == "__main__":
    main()
