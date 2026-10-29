<?php
declare(strict_types=1);

const WB_STATUSES = ['new', 'contacted', 'site_visit', 'quoted', 'won', 'lost'];
const WB_PROJECTS = ['New house construction', 'Extension', 'Renovation', 'Concrete, block or structural work', 'Repairs / maintenance', 'Estimate / not sure yet'];
const WB_SIZES = ['Small', 'Medium', 'Large', 'Not sure'];
const WB_PLANS = ['Yes, approved', 'Yes, not yet approved', 'Sketches or photos only', 'No plans yet'];
const WB_BUDGETS = ['Under 3M', '3M-8M', '8M-20M', '20M+', 'Not decided'];
const WB_TIMEFRAMES = ['Within 3 months', '3-6 months', '6+ months', 'Just planning'];
const WB_INTENTS = ['quote', 'site_visit', 'call'];

function wb_config(): array
{
    static $cfg = null;
    if ($cfg === null) {
        $file = getenv('WB_CONFIG_FILE') ?: __DIR__ . '/config.php';
        if (!is_file($file)) {
            throw new RuntimeException('config.php is missing');
        }
        $cfg = require $file;
    }
    return $cfg;
}

function wb_db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $c = wb_config();
        $dsn = $c['db_dsn'] !== '' ? $c['db_dsn'] : 'mysql:host=' . $c['db_host'] . ';dbname=' . $c['db_name'] . ';charset=utf8mb4';
        $pdo = new PDO($dsn, $c['db_user'] ?? null, $c['db_pass'] ?? null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
    }
    return $pdo;
}

function wb_now(): string
{
    return gmdate('Y-m-d H:i:s');
}

function wb_ip_hash(): string
{
    return hash('sha256', (wb_config()['ip_salt'] ?? '') . '|' . ($_SERVER['REMOTE_ADDR'] ?? ''));
}

function wb_json(int $code, array $body): never
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($body, JSON_UNESCAPED_UNICODE);
    exit;
}

/** True when the request comes from this site or an allowed origin (or has no Origin header, e.g. a server-side call). */
function wb_origin_ok(): bool
{
    $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
    if ($origin === '') {
        return true;
    }
    if (in_array($origin, wb_config()['allowed_origins'] ?? [], true)) {
        return true;
    }
    $host = parse_url($origin, PHP_URL_HOST);
    return is_string($host) && strcasecmp($host, explode(':', $_SERVER['HTTP_HOST'] ?? '')[0]) === 0;
}

function wb_clean(mixed $v, int $max): string
{
    $s = is_string($v) ? trim($v) : '';
    $s = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $s) ?? '';
    return mb_substr($s, 0, $max);
}
