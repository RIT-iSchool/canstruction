// tiny tracking helper
// - counts a page view when the page loads
// - counts a click on anything that has a data-track="..." attribute
// no cookies, no names, no ip addresses. just a random id saved in the browser
// so we can tell "10 views from 3 people" apart from "10 views from 10 people".

(function () {
  // where events get sent. change this if the server lives somewhere else later.
  const ENDPOINT = window.TRACK_ENDPOINT || "/api/track";

  // random id for this browser, made once and reused
  function visitorId() {
    try {
      let id = localStorage.getItem("canstruction_visitor");
      if (!id) {
        id = Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem("canstruction_visitor", id);
      }
      return id;
    } catch {
      return "anonymous"; // private browsing etc, still count the view
    }
  }

  // how did they get here? the qr code adds ?src=qr to the link
  function source() {
    const src = new URLSearchParams(location.search).get("src");
    if (src) return src;
    if (document.referrer && !document.referrer.startsWith(location.origin)) return "link";
    return "direct";
  }

  function send(event) {
    const body = JSON.stringify({
      ...event,
      page: location.pathname,
      source: source(),
      visitor: visitorId(),
    });

    // sendBeacon still delivers even if the click opens a new page right away
    if (navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }));
    } else {
      fetch(ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
    }
  }

  window.track = {
    view: () => send({ type: "view" }),
    click: (target, label, sponsor) => send({ type: "click", target, label, sponsor }),
  };

  // one listener for the whole page, catches every [data-track] click
  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-track]");
    if (!el) return;
    window.track.click(el.dataset.track, el.dataset.trackLabel || el.textContent.trim().slice(0, 80), el.dataset.sponsor || "");
  });

  // count the view
  window.track.view();
})();
