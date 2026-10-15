# RIT Canstruction Sponsor Page

A sponsor page for RIT Canstruction (2026 theme: The Three Little Pigs and the Big Bad Wolf), plus a tiny tracker that counts page views and button clicks.

## What's in here

```
2026_sponsor_page/
└── public/              upload everything in here to the web server
    ├── index.html       the sponsor page (pig, wolf, and house drawings are in the <svg> at the top of <body>)
    ├── stats.html       the stats dashboard
    ├── tracker.js       sends views/clicks to api/track.php
    ├── api/
    │   ├── config.php   settings (stats password, where data is saved, timezone)
    │   ├── track.php    saves each view/click
    │   └── stats.php    adds up the numbers for stats.html
    └── data/
        ├── events.php   where views/clicks get saved (created automatically)
        └── .htaccess    blocks anyone from downloading the data folder
```

The server only needs PHP (7.4 or newer). No Node.js, no database.

## Put it on the server

1. Upload everything inside `public/` (including the hidden `.htaccess` file in `data/`) to the folder the page should live in.
2. Make sure the `data/` folder is writable by PHP. On most shared hosts it already is. If clicks don't show up, set the folder's permissions to `755` (or `775`) in the host's file manager.
3. Open the page, click a button, then open `stats.html` in the same folder. The click should be there.

## Run it on your computer

You need PHP installed (on a Mac: `brew install php`).

```bash
cd 2026_sponsor_page
php -S localhost:8000 -t public
```

Then open:

- **Sponsor page:** http://localhost:8000
- **Stats page:** http://localhost:8000/stats.html (refreshes every 10 seconds)

To stop it, press `Ctrl + C`.

> Open the pages through `http://localhost:8000`. If you double-click `index.html`, the page shows up but views and clicks won't save.

## What gets tracked

| Stat            | How it works                                                                                                                                                                |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Page views      | +1 every time the page loads                                                                                                                                                |
| Unique visitors | a random ID saved in each browser (no names, no IP addresses)                                                                                                               |
| QR code scans   | counts visits whose link ends in `?src=qr`. The page doesn't show a QR code anymore, so add `?src=qr` to any QR you print (like on the display sign) to keep counting scans |
| Button clicks   | anything with `data-track="..."` gets counted, with its sponsor                                                                                                             |

Tracked buttons right now: each sponsor's logo in the top strip, their big logo, their "Visit" button, the hero's "Meet our sponsors" button, the "Huff and puff" button, and both links back to ritcanstruction.org.

**To track a new button**, add `data-track` to it:

```html
<a href="..." data-track="donate-button" data-track-label="Donate button"
  >Donate</a
>
```

## Reset the numbers

Delete `data/events.php` on the server. A fresh one gets made on the next visit.

## How the data stays private

- `data/events.php` starts with a line of PHP that stops right away, so if someone opens it in a browser they get an empty page instead of the data.
- `data/.htaccess` also blocks the whole folder on Apache servers.
- No names or IP addresses are saved, only a random ID per browser.
- Text that comes in gets cleaned (no `<`, `>`, quotes, etc.) and size-limited, and saving stops if the file ever passes 5 MB.
- To add a password to the stats page, set `STATS_KEY` in `api/config.php`, then open `stats.html?key=yourpassword`.

## Editing sponsors

Everything about the sponsors lives in the `SPONSORS` list near the bottom of `public/index.html`. Each sponsor's colors and background pattern are the `.theme-<id>` CSS classes near the top.

Sponsors show up in the order they're listed, and every sponsor gets the same size card (3 across on a computer, 2 on a tablet, 1 on a phone). The order right now: Garlock, Iter Opus, Pittsford FCU, Higher Booking, Matthews & Fields, TrippWells.

To hide a sponsor without deleting it, give it `show: false` (EC4B is set up this way right now).

To add a sponsor: copy a sponsor in the list, give it a new `id`, keep `tier: 3`, and add a `.theme-<id>` block in the CSS (copy one of the existing ones and change the colors). Then add its `id` to the `NAMES` list in `stats.html`.

## Before it goes live

1. **Logos:** three logos load from the team's existing `ritcanstruction.org/assets/img/sponsorLogos/` folder. EC4B's loads from their own website, so save a copy of it into that folder and update the path.
2. **QR code:** point it at the page's real address with `?src=qr` on the end (for example `https://example.com/sponsors/?src=qr`) so scans show up on the stats page.
