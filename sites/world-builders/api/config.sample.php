<?php
// Copy this file to config.php (same folder) and fill in the values. config.php is never committed
// and is blocked from web access by api/.htaccess.
return [
    // From hPanel > Databases > Management. Hostinger prefixes names, e.g. u123456789_wbc.
    'db_host' => 'localhost',
    'db_name' => 'u000000000_wbc',
    'db_user' => 'u000000000_wbc',
    'db_pass' => 'CHANGE_ME',
    'db_dsn'  => '', // leave empty in production (only used by the automated tests)

    // Where new-enquiry emails go, and the sender address (use a mailbox on your own domain).
    'notify_to' => 'gayle.r.ricardo@gmail.com',
    'mail_from' => 'enquiries@worldbuildersconstruction.com',

    // Only these sites may post enquiries from a browser.
    'allowed_origins' => ['https://worldbuildersconstruction.com', 'https://www.worldbuildersconstruction.com'],

    // Long random string; used to hash visitor IPs so raw IPs are never stored.
    'ip_salt' => 'CHANGE_ME_TO_A_LONG_RANDOM_STRING',
    'rate_limit_per_hour' => 8,

    // Admin viewer at /admin/. Create the hash with:  php -r "echo password_hash('YourPassword', PASSWORD_DEFAULT);"
    'admin_user' => 'ricardo',
    'admin_password_hash' => '',
];
