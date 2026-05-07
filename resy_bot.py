import os
import json
import asyncio
import smtplib
import httpx
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from playwright.async_api import async_playwright

RESY_TOKEN = os.environ.get("RESY_TOKEN")
if not RESY_TOKEN:
    TOKEN_PATH = os.path.expanduser("~/resy-bot/resy_token.txt")
    with open(TOKEN_PATH, "r") as f:
        RESY_TOKEN = f.read().strip()

GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
RESY_API_KEY = os.environ.get("RESY_API_KEY")

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

CITY_COORDS = {
    "new-york-ny": (40.7128, -74.0060),
    "los-angeles-ca": (34.0522, -118.2437),
    "chicago-il": (41.8781, -87.6298),
    "san-francisco-ca": (37.7749, -122.4194),
    "miami-fl": (25.7617, -80.1918),
    "boston-ma": (42.3601, -71.0589),
    "washington-dc": (38.9072, -77.0369),
    "seattle-wa": (47.6062, -122.3321),
    "austin-tx": (30.2672, -97.7431),
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "restaurants.json")
with open(CONFIG_PATH) as f:
    config = json.load(f)

PARTY_SIZE = config["party_size"]
CITY = config.get("city", "new-york-ny")
PHONE_NUMBER = config.get("phone_number")
PHONE_CARRIER = config.get("phone_carrier")
RESTAURANTS = [r for r in config["restaurants"] if r["platform"] == "resy" and r.get("active", True)]

_url_cache = {}


def get_sms_address():
    if PHONE_NUMBER and PHONE_CARRIER:
        gateway = CARRIER_GATEWAYS.get(PHONE_CARRIER.lower())
        if gateway:
            return f"{PHONE_NUMBER}@{gateway}"
    return None


async def find_resy_url(name, city):
    if name in _url_cache:
        return _url_cache[name]

    lat, lon = CITY_COORDS.get(city, (40.7128, -74.0060))
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.resy.com/3/venue/search",
                params={"query": name, "geo[lat]": lat, "geo[lon]": lon},
                headers={
                    "Authorization": f'ResyAPI api_key="{RESY_API_KEY}"',
                    "X-Resy-Auth-Token": RESY_TOKEN,
                    "User-Agent": "Mozilla/5.0",
                },
                timeout=10,
            )
        if resp.status_code == 200:
            data = resp.json()
            venues = (
                data.get("search", {}).get("hits")
                or data.get("results", {}).get("venues")
                or []
            )
            for venue in venues:
                slug = venue.get("url_slug") or (venue.get("location") or {}).get("url_slug")
                if slug:
                    url = f"https://resy.com/cities/{city}/venues/{slug}"
                    _url_cache[name] = url
                    return url
        else:
            print(f"  Resy search returned {resp.status_code} for '{name}'")
    except Exception as e:
        print(f"  Resy lookup error for '{name}': {e}")

    print(f"  Could not auto-find Resy URL for '{name}' - add a 'url' field to restaurants.json")
    return None


def time_slots_12h(time_start, time_end):
    start = datetime.strptime(time_start, "%H:%M")
    end = datetime.strptime(time_end, "%H:%M")
    slots = []
    t = start
    while t <= end:
        hour = t.hour % 12 or 12
        slots.append(f"{hour}:{t.strftime('%M')} {'AM' if t.hour < 12 else 'PM'}")
        t += timedelta(minutes=30)
    return slots


def send_notifications(restaurant, date, time_slot):
    subject = f"Booked: {restaurant} on {date} at {time_slot}!"
    body = f"""
Your reservation has been booked automatically!

Restaurant: {restaurant}
Date: {date}
Time: {time_slot}
Party size: {PARTY_SIZE}

Check your Resy app to confirm.
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


async def inject_token(context):
    await context.add_cookies([{
        "name": "production_refresh_token",
        "value": RESY_TOKEN,
        "domain": ".resy.com",
        "path": "/"
    }])


async def book_restaurant(page, restaurant, date):
    name = restaurant["name"]
    city = restaurant.get("city", CITY)
    times = time_slots_12h(restaurant["time_start"], restaurant["time_end"])

    url = restaurant.get("url") or await find_resy_url(name, city)
    if not url:
        return False

    print(f"\nChecking {name} for {date}...")

    await page.goto(f"{url}?date={date}&seats={PARTY_SIZE}")
    await page.wait_for_timeout(3000)

    for time_slot in times:
        print(f"  Looking for {time_slot}...")
        try:
            slot = page.locator(f'button:has-text("{time_slot}")')
            if await slot.count() > 0:
                print(f"  Found slot at {time_slot} - booking now!")
                await slot.first.click()
                await page.wait_for_timeout(2000)

                reserve_btn = page.locator('button:has-text("Reserve")')
                if await reserve_btn.count() > 0:
                    await reserve_btn.first.click()
                    await page.wait_for_timeout(3000)
                    print(f"  Booked {name} at {time_slot} on {date}!")
                    send_notifications(name, date, time_slot)
                    return True
        except Exception as e:
            print(f"  Error trying {time_slot}: {e}")
            continue

    print(f"  No available slots found for {name} on {date}")
    return False


async def main():
    print("Starting Resy bot...")
    print(f"Looking for tables for {PARTY_SIZE} people")
    print(f"Checking {len(RESTAURANTS)} restaurants\n")

    async with async_playwright() as p:
        headless = os.environ.get("GITHUB_ACTIONS") == "true"
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        await inject_token(context)
        page = await context.new_page()

        results = []
        for restaurant in RESTAURANTS:
            for date in restaurant["dates"]:
                booked = await book_restaurant(page, restaurant, date)
                results.append({
                    "restaurant": restaurant["name"],
                    "date": date,
                    "booked": booked
                })
                await asyncio.sleep(2)

        print("\n--- RESULTS ---")
        for r in results:
            status = "BOOKED" if r["booked"] else "NOT AVAILABLE"
            print(f"{r['restaurant']} ({r['date']}): {status}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
