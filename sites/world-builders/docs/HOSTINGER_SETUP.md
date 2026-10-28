# Hostinger setup: World Builders Construction

The site is plain HTML plus a small PHP + MySQL backend, which is what Hostinger web hosting runs natively.
Nothing here needs a build step.

## What gets uploaded (into `public_html`)

| Upload | Do NOT upload |
|---|---|
| `index.html`, `images/`, `api/`, `admin/`, `.htaccess`, `robots.txt`, `sitemap.xml` | `database/`, `docs/`, `README.md` (the root `.htaccess` blocks them anyway) |

## Path A: by hand in hPanel (about 15 minutes)

1. **Database.** hPanel > Databases > Management > create a database + user. Hostinger prefixes both
   (for example `u123456789_wbc`). Save the password.
2. **Tables.** hPanel > Databases > phpMyAdmin > select that database > Import > choose `database/schema.sql`.
   You should see two tables: `leads` and `login_attempts`.
3. **Upload the site** (File Manager, FTP or Git deploy) into `public_html`.
4. **Config.** In `public_html/api/` copy `config.sample.php` to `config.php` and fill in:
   - `db_name`, `db_user`, `db_pass` from step 1 (`db_host` stays `localhost`)
   - `notify_to` (where enquiry emails go) and `mail_from` (a mailbox you create on the domain, e.g. `enquiries@worldbuildersconstruction.com`, in hPanel > Emails)
   - `allowed_origins` (the real domain, with and without `www`)
   - `ip_salt`: any long random string
   - `admin_password_hash`: run `php -r "echo password_hash('YourStrongPassword', PASSWORD_DEFAULT);"` anywhere PHP is installed, or use any bcrypt generator, and paste the result
5. **SSL.** hPanel > Security > SSL: make sure it is active, then the `.htaccess` HTTPS redirect works.
6. **Test** (below).

## Path B: through the Hostinger MCP / API (Claude can do steps 1-3)

The official server is [`hostinger/api-mcp-server`](https://github.com/hostinger/api-mcp-server). Its hosting tools include
`hosting_databases_create`, `hosting_databases_list`, `hosting_databases_change-password`, `hosting_databases_phpmyadmin-link`,
`hosting_deploy`, `hosting_ssl_install` and `hosting_domains_*`.

1. In the client's Hostinger account create an API token (hPanel > Profile/Account > API; see developers.hostinger.com).
   The token is the client's credential: never paste it into chat or commit it.
2. Add the server to the MCP client (Claude Code, Claude Desktop, Cursor):

```json
{
  "mcpServers": {
    "hostinger-api": {
      "command": "hostinger-api-mcp",
      "env": { "HOSTINGER_API_TOKEN": "<set in your local MCP settings, never committed>" }
    }
  }
}
```

3. Ask Claude: "Using the Hostinger MCP, list this account's hosting websites, create a MySQL database and user for
   world-builders on that site, and give me the phpMyAdmin link." Then import `database/schema.sql` in phpMyAdmin
   (the MCP creates the database; the schema import and `config.php` are still manual so the password never passes through chat).
4. Optional: `hosting_deploy` can publish the site files; `hosting_ssl_status` confirms SSL.

Tool names and options change between versions: check the server's README for the current list.

## Test checklist (do all of these on the live domain)

- [ ] Home page loads over `https://`, `http://` redirects to it, no mixed-content warnings.
- [ ] Submit the form with **Book a site visit** and again with **Request a quote**. Each should show the "received" screen, not the WhatsApp fallback.
- [ ] A row appears in phpMyAdmin `leads` (or in `/admin/`), with `intent` = `site_visit` / `quote`.
- [ ] The notification email arrives (check spam the first time). If not, the lead is still saved with `notified = 0`; fix `mail_from`/mailbox and the admin shows "email not sent".
- [ ] `/admin/` asks for login; wrong password 5 times locks that IP for 15 minutes; status changes and CSV export work.
- [ ] `https://domain/api/config.php` and `https://domain/database/schema.sql` return 403/404.
- [ ] Tap Call now and WhatsApp on a phone. Confirm both numbers are right (see "Open items" in README).
- [ ] Optional hardening: password-protect `/admin/` in hPanel > Advanced > Password Protect Directories (second lock).

## Backups and privacy

- hPanel > Backups keeps site and database backups; export `leads` as CSV from `/admin/` monthly as well.
- Visitor IPs are stored only as a salted SHA-256 hash (rate limiting). Leads contain names and phone numbers: keep `/admin/` access to the owner only.
