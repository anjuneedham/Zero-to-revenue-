<?php
declare(strict_types=1);
require __DIR__ . '/common.php';

try {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        header('Allow: POST');
        wb_json(405, ['ok' => false, 'error' => 'method_not_allowed']);
    }
    if (!wb_origin_ok()) {
        wb_json(403, ['ok' => false, 'error' => 'origin_not_allowed']);
    }
    $raw = file_get_contents('php://input', false, null, 0, 20001);
    if ($raw === false || strlen($raw) > 20000) {
        wb_json(413, ['ok' => false, 'error' => 'too_large']);
    }
    $in = json_decode($raw, true);
    if (!is_array($in)) {
        wb_json(400, ['ok' => false, 'error' => 'invalid_json']);
    }
    // Honeypot: bots fill the hidden field. Pretend success, store nothing.
    if (wb_clean($in['company_website'] ?? '', 200) !== '') {
        wb_json(200, ['ok' => true]);
    }

    $name = wb_clean($in['name'] ?? '', 120);
    $phone = wb_clean($in['phone'] ?? '', 32);
    $email = wb_clean($in['email'] ?? '', 190);
    $location = wb_clean($in['location'] ?? '', 120);
    $project = wb_clean($in['project'] ?? '', 60);
    $size = wb_clean($in['size'] ?? '', 20);
    $plans = wb_clean($in['plans'] ?? '', 30);
    $budget = wb_clean($in['budget_jmd'] ?? '', 20);
    $timeframe = wb_clean($in['timeframe'] ?? '', 20);
    $message = wb_clean($in['message'] ?? '', 2000);
    $intent = wb_clean($in['intent'] ?? 'quote', 20);
    $variant = wb_clean($in['variant'] ?? '', 40);
    $page = wb_clean($in['page'] ?? '', 255);

    $errors = [];
    if (mb_strlen($name) < 2) $errors[] = 'name';
    if (strlen(preg_replace('/\D/', '', $phone) ?? '') < 7 || !preg_match('/^[0-9+()\-.\s]{7,32}$/', $phone)) $errors[] = 'phone';
    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) $errors[] = 'email';
    if ($location === '') $errors[] = 'location';
    if (!in_array($project, WB_PROJECTS, true)) $errors[] = 'project';
    if (!in_array($size, WB_SIZES, true)) $errors[] = 'size';
    if (!in_array($plans, WB_PLANS, true)) $errors[] = 'plans';
    if (!in_array($budget, WB_BUDGETS, true)) $errors[] = 'budget_jmd';
    if (!in_array($timeframe, WB_TIMEFRAMES, true)) $errors[] = 'timeframe';
    if (!in_array($intent, WB_INTENTS, true)) $intent = 'quote';
    if (!preg_match('/^[a-z0-9_\-]{0,40}$/i', $variant)) $variant = '';
    if ($errors) {
        wb_json(422, ['ok' => false, 'error' => 'invalid', 'fields' => $errors]);
    }

    $pdo = wb_db();
    $ipHash = wb_ip_hash();
    $limit = (int) (wb_config()['rate_limit_per_hour'] ?? 8);
    $recent = $pdo->prepare('SELECT COUNT(*) FROM leads WHERE ip_hash = ? AND created_at > ?');
    $recent->execute([$ipHash, gmdate('Y-m-d H:i:s', time() - 3600)]);
    if ((int) $recent->fetchColumn() >= $limit) {
        wb_json(429, ['ok' => false, 'error' => 'rate_limited']);
    }

    $now = wb_now();
    $pdo->prepare(
        'INSERT INTO leads (created_at, updated_at, name, phone, email, location, project, size, plans, budget_jmd, timeframe, message, intent, variant, page, ip_hash, user_agent)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
    )->execute([
        $now, $now, $name, $phone, $email !== '' ? $email : null, $location, $project, $size, $plans, $budget, $timeframe,
        $message !== '' ? $message : null, $intent, $variant !== '' ? $variant : null, $page !== '' ? $page : null,
        $ipHash, mb_substr($_SERVER['HTTP_USER_AGENT'] ?? '', 0, 255),
    ]);
    $id = (int) $pdo->lastInsertId();

    // Email the owner. A mail failure never loses the lead: it is already saved and flagged notified=0.
    $cfg = wb_config();
    $oneLine = static fn(string $s): string => trim(preg_replace('/[\r\n]+/', ' ', $s) ?? '');
    $label = $intent === 'site_visit' ? 'SITE VISIT REQUEST' : ($intent === 'call' ? 'CALL-BACK REQUEST' : 'Quote enquiry');
    $body = "$label (#$id)\n\nName: $name\nPhone/WhatsApp: $phone\nEmail: " . ($email ?: '-') . "\nLocation: $location\n"
        . "Project: $project\nSize: $size\nPlans: $plans\nBudget (JMD): $budget\nStart: $timeframe\n"
        . ($message !== '' ? "Notes: $message\n" : '') . "\nReceived: $now UTC\n";
    $headers = 'From: World Builders Website <' . $oneLine($cfg['mail_from']) . ">\r\nContent-Type: text/plain; charset=utf-8"
        . ($email !== '' ? "\r\nReply-To: " . $oneLine($email) : '');
    $sent = @mail($cfg['notify_to'], '=?UTF-8?B?' . base64_encode("$label: " . $oneLine($name) . ' - ' . $oneLine($location)) . '?=', $body, $headers);
    if ($sent) {
        $pdo->prepare('UPDATE leads SET notified = 1 WHERE id = ?')->execute([$id]);
    }

    wb_json(200, ['ok' => true, 'id' => $id]);
} catch (Throwable $e) {
    error_log('[wb lead] ' . $e->getMessage());
    wb_json(500, ['ok' => false, 'error' => 'server_error']);
}
