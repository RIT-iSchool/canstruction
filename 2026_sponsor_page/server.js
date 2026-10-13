// tiny server for the sponsor page + view/click tracking
// no npm install needed, it only uses stuff that comes with node
//
// run it:   node server.js
// then open http://localhost:3000            (sponsor page)
//       and http://localhost:3000/stats.html (the numbers)

const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, "public");
const DATA_FILE = path.join(__dirname, "data", "analytics.json");

// optional: set a password for the stats page, e.g.  STATS_KEY=cans123 node server.js
// then open /stats.html?key=cans123
const STATS_KEY = process.env.STATS_KEY || "";

// ---------- saving + loading data ----------
// every view/click is saved as one small "event" in a json file.
// totally fine for a club site. if it ever gets huge, move to a real database.
function loadData() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
  } catch {
    return { events: [] }; // first run, nothing saved yet
  }
}

let data = loadData();
let saveTimer = null;

// wait a moment before writing so a burst of clicks = one file write
function saveSoon() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
  }, 500);
}

// keeps strings short + plain so nobody can stuff junk into the file
function clean(value, max = 80) {
  if (typeof value !== "string") return "";
  return value.replace(/[^\w\s.,:&'()\-\/]/g, "").trim().slice(0, max);
}

// ---------- turning raw events into numbers ----------
function dayKey(time) {
  // yyyy-mm-dd in the server's timezone
  return new Date(time).toLocaleDateString("en-CA");
}

function buildStats() {
  const views = data.events.filter((e) => e.type === "view");
  const clicks = data.events.filter((e) => e.type === "click");

  // unique visitors = how many different browsers viewed the page
  const uniqueVisitors = new Set(views.map((e) => e.visitor)).size;

  // where people came from (qr = scanned the code)
  const bySource = {};
  views.forEach((e) => (bySource[e.source] = (bySource[e.source] || 0) + 1));

  // clicks grouped by button
  const byButton = {};
  clicks.forEach((e) => {
    if (!byButton[e.target]) byButton[e.target] = { target: e.target, label: e.label, sponsor: e.sponsor, count: 0 };
    byButton[e.target].count++;
  });

  // clicks grouped by sponsor (adds up all of that sponsor's buttons)
  const bySponsor = {};
  clicks.filter((e) => e.sponsor).forEach((e) => (bySponsor[e.sponsor] = (bySponsor[e.sponsor] || 0) + 1));

  // views per day for the last 14 days (days with 0 still show up)
  const viewsByDay = [];
  for (let i = 13; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = dayKey(d);
    viewsByDay.push({ day: key, count: views.filter((e) => dayKey(e.time) === key).length });
  }

  return {
    totals: {
      views: views.length,
      uniqueVisitors,
      clicks: clicks.length,
      qrScans: bySource.qr || 0,
    },
    bySource,
    byButton: Object.values(byButton).sort((a, b) => b.count - a.count),
    bySponsor: Object.entries(bySponsor)
      .map(([sponsor, count]) => ({ sponsor, count }))
      .sort((a, b) => b.count - a.count),
    viewsByDay,
    recent: data.events.slice(-25).reverse(),
  };
}

// ---------- serving the html/css/js files ----------
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
};

function serveFile(req, res) {
  let urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (urlPath === "/") urlPath = "/index.html";

  // path.normalize + the startsWith check stops "../" tricks from reading other files
  const filePath = path.normalize(path.join(PUBLIC_DIR, urlPath));
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    return res.end("nope");
  }

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404);
      return res.end("not found");
    }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(filePath)] || "application/octet-stream" });
    res.end(content);
  });
}

// ---------- the actual server ----------
const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://x");

  // the page sends views + clicks here
  if (req.method === "POST" && url.pathname === "/api/track") {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 2000) req.destroy(); // way too big, ignore it
    });
    req.on("end", () => {
      try {
        const e = JSON.parse(body);
        if (e.type !== "view" && e.type !== "click") throw new Error("bad type");

        data.events.push({
          type: e.type,
          target: clean(e.target),
          label: clean(e.label),
          sponsor: clean(e.sponsor, 40),
          source: clean(e.source, 30) || "direct",
          visitor: clean(e.visitor, 40),
          page: clean(e.page, 60),
          time: new Date().toISOString(),
        });
        saveSoon();
        res.writeHead(204);
        res.end();
      } catch {
        res.writeHead(400);
        res.end("bad event");
      }
    });
    return;
  }

  // the stats page reads the numbers from here
  if (req.method === "GET" && url.pathname === "/api/stats") {
    if (STATS_KEY && url.searchParams.get("key") !== STATS_KEY) {
      res.writeHead(401, { "Content-Type": "application/json" });
      return res.end(JSON.stringify({ error: "wrong or missing key" }));
    }
    res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
    return res.end(JSON.stringify(buildStats()));
  }

  // everything else = a normal file from /public
  serveFile(req, res);
});

server.listen(PORT, () => {
  console.log(`sponsor page:  http://localhost:${PORT}`);
  console.log(`stats page:    http://localhost:${PORT}/stats.html${STATS_KEY ? "?key=" + STATS_KEY : ""}`);
});
