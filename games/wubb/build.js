// Copies the static game into www/ for Capacitor.
const fs = require("fs"), path = require("path");
const files = ["index.html", "game.js", "levels.js", "manifest.webmanifest", "sw.js"];
fs.rmSync("www", { recursive: true, force: true });
fs.mkdirSync("www/icons", { recursive: true });
files.forEach(f => fs.copyFileSync(f, path.join("www", f)));
fs.readdirSync("icons").forEach(f => fs.copyFileSync(path.join("icons", f), path.join("www/icons", f)));
console.log("built www/");
