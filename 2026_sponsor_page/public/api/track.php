<?php
// the sponsor page sends views + clicks here (see tracker.js)
require __DIR__ . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  header('Allow: POST');
  send_json(['error' => 'POST only'], 405);
}

// anything bigger than 2000 characters isn't a real event, ignore it
$body = stream_get_contents(fopen('php://input', 'r'), 2001);
if ($body === false || strlen($body) > 2000) send_json(['error' => 'too big'], 413);

$e = json_decode($body, true);
if (!is_array($e) || !isset($e['type']) || ($e['type'] !== 'view' && $e['type'] !== 'click')) {
  send_json(['error' => 'bad event'], 400);
}

$source = clean($e['source'] ?? '', 30);
$saved = save_event([
  'type'    => $e['type'],
  'target'  => clean($e['target'] ?? ''),
  'label'   => clean($e['label'] ?? ''),
  'sponsor' => clean($e['sponsor'] ?? '', 40),
  'source'  => $source !== '' ? $source : 'direct',
  'visitor' => clean($e['visitor'] ?? '', 40),
  'page'    => clean($e['page'] ?? '', 60),
  'time'    => gmdate('Y-m-d\TH:i:s\Z'),
]);

if (!$saved) send_json(['error' => 'could not save'], 507);
http_response_code(204);
