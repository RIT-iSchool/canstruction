<?php
// the stats page reads the numbers from here (see stats.html)
require __DIR__ . '/config.php';

if (STATS_KEY !== '' && !hash_equals(STATS_KEY, (string)($_GET['key'] ?? ''))) {
  send_json(['error' => 'wrong or missing key'], 401);
}

$events = load_events();
$views = array_values(array_filter($events, function ($e) { return ($e['type'] ?? '') === 'view'; }));
$clicks = array_values(array_filter($events, function ($e) { return ($e['type'] ?? '') === 'click'; }));

// unique visitors = how many different browsers viewed the page
$visitors = [];
foreach ($views as $e) $visitors[$e['visitor'] ?? ''] = true;

// where people came from (qr = scanned the code)
$bySource = [];
foreach ($views as $e) {
  $src = $e['source'] ?? 'direct';
  $bySource[$src] = ($bySource[$src] ?? 0) + 1;
}

// clicks grouped by button
$byButton = [];
foreach ($clicks as $e) {
  $t = $e['target'] ?? '';
  if (!isset($byButton[$t])) {
    $byButton[$t] = ['target' => $t, 'label' => $e['label'] ?? '', 'sponsor' => $e['sponsor'] ?? '', 'count' => 0];
  }
  $byButton[$t]['count']++;
}
$byButton = array_values($byButton);
usort($byButton, function ($a, $b) { return $b['count'] - $a['count']; });

// clicks grouped by sponsor (adds up all of that sponsor's buttons)
$sponsorCounts = [];
foreach ($clicks as $e) {
  if (empty($e['sponsor'])) continue;
  $sponsorCounts[$e['sponsor']] = ($sponsorCounts[$e['sponsor']] ?? 0) + 1;
}
arsort($sponsorCounts);
$bySponsor = [];
foreach ($sponsorCounts as $sponsor => $count) $bySponsor[] = ['sponsor' => $sponsor, 'count' => $count];

// views per day for the last 14 days (days with 0 still show up)
$dayCounts = [];
foreach ($views as $e) {
  $day = date('Y-m-d', strtotime($e['time'] ?? ''));
  $dayCounts[$day] = ($dayCounts[$day] ?? 0) + 1;
}
$viewsByDay = [];
for ($i = 13; $i >= 0; $i--) {
  $day = date('Y-m-d', strtotime("-$i days"));
  $viewsByDay[] = ['day' => $day, 'count' => $dayCounts[$day] ?? 0];
}

send_json([
  'totals' => [
    'views' => count($views),
    'uniqueVisitors' => count($visitors),
    'clicks' => count($clicks),
    'qrScans' => $bySource['qr'] ?? 0,
  ],
  'bySource' => (object)$bySource,
  'byButton' => $byButton,
  'bySponsor' => $bySponsor,
  'viewsByDay' => $viewsByDay,
  'recent' => array_reverse(array_slice($events, -25)),
]);
