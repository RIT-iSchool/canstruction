# RIT Canstruction Sponsor Page

A sponsor page for RIT Canstruction (2026 theme: The Three Little Pigs and the Big Bad Wolf), plus a tiny tracker that counts page views and button clicks.

## What's in here

```
2026_sponsor_page/
├── server.js            the server: shows the pages + saves views/clicks
├── data/analytics.json  where views/clicks get saved (created automatically)
└── public/
    ├── index.html       the sponsor page (pig, wolf, and house drawings are in the <svg> at the top of <body>)
    ├── stats.html       the stats dashboard
    └── tracker.js       the bit that sends views/clicks to the server
```

## Run it on localhost

You only need Node.js (any version from the last few years). No `npm install`.

```bash
cd 2026_sponsor_page
node server.js
```

Then open:

- **Sponsor page:** http://localhost:3000
- **Stats page:** http://localhost:3000/stats.html (refreshes every 10 seconds)

To stop the server, press `Ctrl + C`.

> Open the pages through `http://localhost:3000`. If you double-click `index.html`, the page shows up but views and clicks won't save.

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

Stop the server, delete `data/analytics.json`, and start it again.

## Editing sponsors

Everything about the sponsors lives in the `SPONSORS` list near the bottom of `public/index.html`. Each sponsor's colors and background pattern are the `.theme-<id>` CSS classes near the top.

Sponsors show up in the order they're listed, and every sponsor gets the same size card (3 across on a computer, 2 on a tablet, 1 on a phone). The order right now: Garlock, Iter Opus, Pittsford FCU, Higher Booking, Matthews & Fields, TrippWells.

To hide a sponsor without deleting it, give it `show: false` (EC4B is set up this way right now).

To add a sponsor: copy a sponsor in the list, give it a new `id`, keep `tier: 3`, and add a `.theme-<id>` block in the CSS (copy one of the existing ones and change the colors). Then add its `id` to the `NAMES` list in `stats.html`.

## Before it goes live

1. **Logos:** three logos load from the team's existing `ritcanstruction.org/assets/img/sponsorLogos/` folder. EC4B's loads from their own website, so save a copy of it into that folder and update the path.
2. **Hosting the tracker:** the tracking only works where `server.js` is running. ritcanstruction.org looks like a static site (plain HTML files), and a static site can't run Node. You have two options:
   - Host `server.js` on a free Node host (like Render or Railway) or an RIT server, and set `window.TRACK_ENDPOINT` to that server's `/api/track` address before `tracker.js` loads.
   - Or, if the page has to stay static, swap the tracker for a hosted analytics tool like GoatCounter, which also counts views and named click events.
