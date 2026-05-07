# reservation-bot
Automated restaurant reservation bot for Resy with OpenTable availability alerts. Runs on GitHub Actions.
# Restaurant Reservation Bot

An automated bot that monitors Resy and OpenTable for available reservations. For Resy, it books automatically the moment a slot opens. For OpenTable, it sends an email alert so you can book manually. Runs entirely in the cloud via GitHub Actions — no computer needs to be on.

## How it works

- Checks your target restaurants every hour via a scheduled GitHub Actions workflow
- Automatically books the first available slot within your preferred time window on Resy
- Sends an email alert when availability opens on OpenTable so you can book manually by clicking the link
- All configuration lives in a single `restaurants.json` file — no code changes needed to add or remove restaurants

## Setup

### 1. Fork this repo

Click the Fork button in the top right on GitHub.

### 2. Add your GitHub Secrets

Go to your repo Settings > Secrets and variables > Actions and add the following:

| Secret | Description |
|---|---|
| `RESY_TOKEN` | Your Resy auth token (see below) |
| `RESY_API_KEY` | Resy API key |
| `GMAIL_EMAIL` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail app password (not your regular password) |
| `RESY_PHONE` | Your 10-digit phone number linked to Resy |

### 3. Get your Resy token

1. Go to resy.com and log in
2. Open browser DevTools (Right click > Inspect)
3. Go to the Network tab
4. Make any action on the page
5. Look for a request with the header `X-Resy-Auth-Token`
6. Copy that value and add it as your `RESY_TOKEN` secret

### 4. Get a Gmail app password

1. Go to your Google account > Security
2. Enable 2-step verification if not already on
3. Search for "App passwords"
4. Create a new app password and copy it

### 5. Configure your restaurants

Edit `restaurants.json` with your target restaurants, dates, and preferred time window:

```json
{
  "party_size": 2,
  "city": "new-york-ny",
  "restaurants": [
    {
      "name": "Don Angie",
      "platform": "resy",
      "active": true,
      "dates": ["2026-03-15"],
      "time_start": "18:00",
      "time_end": "20:00"
    }
  ]
}
```

Set `"active": false` on any restaurant once it's been booked to stop the bot from checking it.

### 6. Enable GitHub Actions

Go to the Actions tab in your repo and enable workflows if prompted. The bot will run every hour automatically. You can also trigger it manually from the Actions tab.

## Supported cities

`new-york-ny`, `los-angeles-ca`, `chicago-il`, `san-francisco-ca`, `miami-fl`, `boston-ma`, `washington-dc`, `seattle-wa`, `austin-tx`

## Built with

- Python 3.12
- Playwright
- GitHub Actions
