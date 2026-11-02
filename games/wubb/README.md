# Wow! Wubb Adventure

A two-player co-op platformer, a fan-made tribute (original art and code, no assets from the TV show).
Collect stars, stomp grumblies, reach the rainbow flag. 3 levels.

- **Play locally:** `npm run serve` then open http://localhost:8080
- **Controls:** 1P: A/D or arrows + W/Up/Space. 2P: P1 A/D + W, P2 arrows. Touch buttons on phones.
- **Web / Vercel:** static site, deploy with Vercel *Root Directory* = `games/wubb` (no build step).
- **Install on phone:** open the Vercel URL in Chrome, menu, "Install app".
- **APK:** push to GitHub; the `Build Wubb APK` workflow produces `wubb-debug.apk` as a downloadable artifact.
  Locally: `npm ci && npm run build && npx cap add android && npx cap sync android && cd android && ./gradlew assembleDebug`.
