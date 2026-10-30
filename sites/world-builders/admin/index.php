<?php
declare(strict_types=1);
require __DIR__ . '/../api/common.php';

header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');
header("Content-Security-Policy: default-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'");
header('X-Frame-Options: DENY');
header('Referrer-Policy: no-referrer');

$https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https';
session_set_cookie_params(['lifetime' => 0, 'path' => '/admin/', 'secure' => $https, 'httponly' => true, 'samesite' => 'Strict']);
session_name('wb_admin');
session_start();

$cfg = wb_config();
$e = static fn(mixed $v): string => htmlspecialchars((string) $v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
$pdo = wb_db();
$error = '';

if (($_GET['logout'] ?? '') === '1') {
    $_SESSION = [];
    session_destroy();
    header('Location: ./');
    exit;
}

/* ---- login ---- */
if (empty($_SESSION['ok'])) {
    if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
        $ip = wb_ip_hash();
        $q = $pdo->prepare('SELECT COUNT(*) FROM login_attempts WHERE ip_hash = ? AND created_at > ?');
        $q->execute([$ip, gmdate('Y-m-d H:i:s', time() - 900)]);
        if ((int) $q->fetchColumn() >= 5) {
            $error = 'Too many attempts. Try again in 15 minutes.';
        } else {
            $hash = (string) ($cfg['admin_password_hash'] ?? '');
            $userOk = hash_equals((string) ($cfg['admin_user'] ?? ''), (string) ($_POST['user'] ?? ''));
            $passOk = $hash !== '' && password_verify((string) ($_POST['pass'] ?? ''), $hash);
            if ($userOk && $passOk) {
                session_regenerate_id(true);
                $_SESSION['ok'] = true;
                $_SESSION['csrf'] = bin2hex(random_bytes(16));
                header('Location: ./');
                exit;
            }
            $pdo->prepare('INSERT INTO login_attempts (ip_hash, created_at) VALUES (?, ?)')->execute([$ip, wb_now()]);
            $error = 'Incorrect username or password.';
        }
    }
    ?><!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sign in | World Builders</title>
<style>body{font:16px system-ui,sans-serif;background:#F1F6FC;display:grid;place-items:center;min-height:100vh;margin:0}form{background:#fff;padding:32px;width:min(360px,92vw);border-top:4px solid #1565D8}
h1{font-size:20px;color:#0A2A66;margin:0 0 18px}label{display:block;font-size:13px;font-weight:600;margin:14px 0 6px}input{width:100%;padding:12px;border:1.5px solid #D3DEEE;font:inherit;box-sizing:border-box}
button{margin-top:20px;width:100%;padding:13px;background:#1565D8;color:#fff;border:0;font:600 15px system-ui;cursor:pointer}.err{color:#b3261e;font-size:13px;margin-top:12px}</style></head><body>
<form method="post" autocomplete="on"><h1>World Builders: enquiries</h1><label for="u">Username</label><input id="u" name="user" required autofocus><label for="p">Password</label><input id="p" name="pass" type="password" required>
<?php if ($error) echo '<div class="err">' . $e($error) . '</div>'; ?><button>Sign in</button></form></body></html><?php
    exit;
}

/* ---- signed in ---- */
$csrf = (string) $_SESSION['csrf'];

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    if (!hash_equals($csrf, (string) ($_POST['csrf'] ?? ''))) {
        http_response_code(400);
        exit('Bad request');
    }
    $id = (int) ($_POST['id'] ?? 0);
    $status = (string) ($_POST['status'] ?? '');
    if ($id > 0 && in_array($status, WB_STATUSES, true)) {
        $pdo->prepare('UPDATE leads SET status = ?, notes = ?, updated_at = ? WHERE id = ?')
            ->execute([$status, mb_substr(trim((string) ($_POST['notes'] ?? '')), 0, 4000) ?: null, wb_now(), $id]);
    }
    header('Location: ./?' . http_build_query(array_filter(['s' => $_POST['s'] ?? '', 'q' => $_POST['q'] ?? ''])));
    exit;
}

$filter = (string) ($_GET['s'] ?? '');
$search = trim((string) ($_GET['q'] ?? ''));
$where = [];
$args = [];
if (in_array($filter, WB_STATUSES, true)) {
    $where[] = 'status = ?';
    $args[] = $filter;
}
if ($search !== '') {
    $like = '%' . addcslashes($search, '%_\\') . '%';
    $where[] = '(name LIKE ? OR phone LIKE ? OR location LIKE ? OR email LIKE ?)';
    array_push($args, $like, $like, $like, $like);
}
$sql = 'SELECT * FROM leads' . ($where ? ' WHERE ' . implode(' AND ', $where) : '') . ' ORDER BY id DESC LIMIT 500';
$st = $pdo->prepare($sql);
$st->execute($args);
$rows = $st->fetchAll();

if (($_GET['export'] ?? '') === 'csv') {
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="world-builders-leads-' . gmdate('Y-m-d') . '.csv"');
    $out = fopen('php://output', 'w');
    fwrite($out, "\xEF\xBB\xBF");
    $cols = ['id', 'created_at', 'status', 'intent', 'name', 'phone', 'email', 'location', 'project', 'size', 'plans', 'budget_jmd', 'timeframe', 'message', 'notes', 'variant'];
    fputcsv($out, $cols);
    foreach ($rows as $r) {
        // Neutralise spreadsheet formula injection from visitor-supplied text.
        fputcsv($out, array_map(static fn($c) => preg_match('/^[=+\-@\t\r]/', (string) $r[$c]) ? "'" . $r[$c] : $r[$c], $cols));
    }
    exit;
}

$counts = $pdo->query('SELECT status, COUNT(*) c FROM leads GROUP BY status')->fetchAll(PDO::FETCH_KEY_PAIR);
$labels = ['new' => 'New', 'contacted' => 'Contacted', 'site_visit' => 'Site visit', 'quoted' => 'Quoted', 'won' => 'Won', 'lost' => 'Lost'];
?><!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Enquiries | World Builders</title>
<style>body{font:15px system-ui,sans-serif;background:#F1F6FC;color:#0E1B33;margin:0}header{background:#0A2A66;color:#fff;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
header a{color:#cfe0ff;margin-left:14px;font-size:14px}main{max-width:1100px;margin:20px auto;padding:0 14px}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.tabs a{padding:8px 14px;background:#fff;border:1px solid #D3DEEE;text-decoration:none;color:#0A2A66;font-weight:600;font-size:13.5px}.tabs a.on{background:#1565D8;color:#fff;border-color:#1565D8}
.card{background:#fff;border:1px solid #D3DEEE;padding:16px;margin-bottom:12px}.card.new{border-left:4px solid #1565D8}.top{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
.top b{font-size:17px}.meta{color:#5B6B86;font-size:13px}dl{display:grid;grid-template-columns:130px 1fr;gap:4px 12px;margin:12px 0;font-size:14px}dt{color:#5B6B86}dd{margin:0}
.tag{display:inline-block;background:#FFE9A8;padding:2px 8px;font-size:12px;font-weight:700;margin-left:6px}form.u{display:grid;grid-template-columns:150px 1fr auto;gap:8px;margin-top:8px}
select,input,textarea,button{font:inherit;padding:9px;border:1.5px solid #D3DEEE}button{background:#1565D8;color:#fff;border:0;font-weight:600;cursor:pointer;padding:9px 16px}
.bar{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}.bar input{flex:1;min-width:200px}@media(max-width:640px){form.u{grid-template-columns:1fr}dl{grid-template-columns:100px 1fr}}</style></head><body>
<header><b>World Builders: enquiries</b><span><a href="?<?= $e(http_build_query(array_filter(['s' => $filter, 'q' => $search, 'export' => 'csv']))) ?>">Export CSV</a><a href="?logout=1">Sign out</a></span></header>
<main>
<div class="tabs"><a href="./" class="<?= $filter === '' ? 'on' : '' ?>">All (<?= (int) array_sum($counts) ?>)</a>
<?php foreach ($labels as $k => $l): ?><a href="?s=<?= $e($k) ?>" class="<?= $filter === $k ? 'on' : '' ?>"><?= $e($l) ?> (<?= (int) ($counts[$k] ?? 0) ?>)</a><?php endforeach; ?></div>
<form class="bar" method="get"><input type="hidden" name="s" value="<?= $e($filter) ?>"><input name="q" value="<?= $e($search) ?>" placeholder="Search name, phone, location, email"><button>Search</button></form>
<?php if (!$rows): ?><div class="card">No enquiries to show.</div><?php endif; ?>
<?php foreach ($rows as $r): $digits = preg_replace('/\D/', '', (string) $r['phone']); ?>
<div class="card <?= $r['status'] === 'new' ? 'new' : '' ?>">
 <div class="top"><b><?= $e($r['name']) ?><?php if ($r['intent'] !== 'quote'): ?><span class="tag"><?= $r['intent'] === 'site_visit' ? 'Site visit request' : 'Call-back' ?></span><?php endif; ?></b>
 <span class="meta">#<?= (int) $r['id'] ?> · <?= $e($r['created_at']) ?> UTC<?= $r['notified'] ? '' : ' · email not sent' ?></span></div>
 <dl><dt>Phone</dt><dd><a href="tel:<?= $e($digits) ?>"><?= $e($r['phone']) ?></a> · <a href="https://wa.me/<?= $e($digits) ?>" rel="noopener">WhatsApp</a></dd>
 <?php if ($r['email']): ?><dt>Email</dt><dd><a href="mailto:<?= $e($r['email']) ?>"><?= $e($r['email']) ?></a></dd><?php endif; ?>
 <dt>Location</dt><dd><?= $e($r['location']) ?></dd><dt>Project</dt><dd><?= $e($r['project']) ?> · <?= $e($r['size']) ?></dd>
 <dt>Plans / budget</dt><dd><?= $e($r['plans']) ?> · JMD <?= $e($r['budget_jmd']) ?></dd><dt>Start</dt><dd><?= $e($r['timeframe']) ?></dd>
 <?php if ($r['message']): ?><dt>Notes</dt><dd><?= nl2br($e($r['message'])) ?></dd><?php endif; ?></dl>
 <form class="u" method="post"><input type="hidden" name="csrf" value="<?= $e($csrf) ?>"><input type="hidden" name="id" value="<?= (int) $r['id'] ?>"><input type="hidden" name="s" value="<?= $e($filter) ?>"><input type="hidden" name="q" value="<?= $e($search) ?>">
 <select name="status" aria-label="Status"><?php foreach ($labels as $k => $l): ?><option value="<?= $e($k) ?>"<?= $r['status'] === $k ? ' selected' : '' ?>><?= $e($l) ?></option><?php endforeach; ?></select>
 <input name="notes" value="<?= $e($r['notes']) ?>" placeholder="Your private notes" maxlength="4000" aria-label="Private notes"><button>Save</button></form>
</div>
<?php endforeach; ?>
</main></body></html>
