# Restaurant Booking Bot 

An automated restaurant reservation bot that monitors booking platforms and books tables automatically the moment availability opens up.

## What it does
- Monitors Resy for available reservations
- Automatically books the first available slot in your preferred time window
- Runs every hour in the cloud — no computer needed
- Sends an email notification when a reservation is booked
- Logs all activity for easy tracking

## Current restaurants (NYC - August 2026)
| Restaurant | Platform | Date | Time Window | Status |
|---|---|---|---|---|
| Theodora | Resy | Aug 12 | 6-8pm | Watching |
| Her Name is Han | Resy | Aug 12 | 6-8pm | Watching |
| Adda | Resy | Aug 12 | 6-8pm | Watching |
| Eyval | Resy | Aug 13 | 6-8pm | Watching |
| Kimura | Resy | Aug 15 | 6-8pm | Watching |
| 8282 | Resy | Aug 16 | 6-8pm | Watching |
| Ramen by Ra | Resy | Aug 16 | 11am-12pm | Watching |
| Samwoojung | Resy | Aug 11 | 6-8pm | Watching |

## Roadmap
- [ ] Add text notifications when a booking is made
- [ ] Support any city, not just NYC
- [ ] Auto-detect booking platform from restaurant name
- [ ] Handle phone-only and walk-in restaurants
- [ ] Build a UI dashboard to manage restaurants and view booking status
- [ ] Expand to OpenTable, Tock, and other platforms

## Setup
Coming soon.

## Built with
- Python 3.12
- Playwright
- GitHub Actions (scheduled runs)
