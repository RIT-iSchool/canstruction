<?php
// settings + shared helpers for track.php and stats.php
// (this file does nothing if someone opens it in a browser)

// optional password for the stats page. empty = no password.
// if you set one, open the stats page as stats.html?key=yourpassword
define('STATS_KEY', '');

// where views/clicks get saved. the file ends in .php on purpose:
// its first line stops php, so opening it in a browser shows nothing.
// if your host lets you, point this at a folder outside the website for extra safety.
define('DATA_DIR', __DIR__ . '/../data');
define('DATA_FILE', DATA_DIR . '/events.php');
define('DATA_GUARD', '<?php http_response_code(404); exit; ?>');

// stop saving new events once the file hits 5 MB so a spammer can't fill the disk.
// that's roughly 25,000 events, way more than the club page will get.
define('MAX_DATA_BYTES', 5 * 1024 * 1024);

// "views per day" uses this timezone
date_default_timezone_set('America/New_York');

// keeps strings short + plain so nobody can stuff junk into the file
function clean($value, $max = 80) {
  if (!is_string($value)) return '';
  $value = preg_replace("/[^A-Za-z0-9_\\s.,:&'()\\-\\/]/", '', $value);
  return substr(trim($value), 0, $max);
}

// adds one event to the end of the data file
function save_event(array $event) {
  if (!is_dir(DATA_DIR)) mkdir(DATA_DIR, 0755, true);

  // first event ever: create the file with the guard line on top.
  // "x" mode only creates it if it doesn't exist yet, so two visitors at once can't both do it
  if (!file_exists(DATA_FILE)) {
    $h = @fopen(DATA_FILE, 'x');
    if ($h) {
      fwrite($h, DATA_GUARD . "\n");
      fclose($h);
    }
  }

  clearstatcache(true, DATA_FILE);
  if (filesize(DATA_FILE) > MAX_DATA_BYTES) return false;

  // LOCK_EX = wait our turn if another visitor is writing at the same moment
  return file_put_contents(DATA_FILE, json_encode($event, JSON_UNESCAPED_SLASHES) . "\n", FILE_APPEND | LOCK_EX) !== false;
}

// reads every saved event (skips the guard line and anything broken)
function load_events() {
  if (!file_exists(DATA_FILE)) return [];
  $h = fopen(DATA_FILE, 'r');
  if (!$h) return [];
  flock($h, LOCK_SH); // don't read halfway through someone else's write
  $events = [];
  while (($line = fgets($h)) !== false) {
    $line = trim($line);
    if ($line === '' || strpos($line, '<?php') === 0) continue;
    $e = json_decode($line, true);
    if (is_array($e)) $events[] = $e;
  }
  flock($h, LOCK_UN);
  fclose($h);
  return $events;
}

function send_json($data, $status = 200) {
  http_response_code($status);
  header('Content-Type: application/json; charset=utf-8');
  header('Cache-Control: no-store');
  header('X-Content-Type-Options: nosniff');
  echo json_encode($data, JSON_UNESCAPED_SLASHES);
  exit;
}
