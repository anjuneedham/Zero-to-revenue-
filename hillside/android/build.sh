#!/usr/bin/env bash
# Builds a signed Hillside APK from ../index.html.
# Needs: JDK 17+, Android SDK (platform 34, build-tools 34.0.0), gradle.
# Env: ANDROID_HOME, HS_KEYSTORE (path to .jks), HS_STORE_PASSWORD, optional HS_KEY_ALIAS.
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
import re
src = open("../index.html").read()
src = re.sub(r'<link rel="manifest"[^>]*>\n?', '', src)
src = re.sub(r'<link rel="icon"[^>]*>\n?', '', src)
src = re.sub(r'<link rel="apple-touch-icon"[^>]*>\n?', '', src)
src = re.sub(r'<script>\s*if \("serviceWorker".*?</script>\n?', '', src, flags=re.S)
src = src.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<script>window.HILLSIDE_NATIVE=true</script>', 1)
open("app/src/main/assets/index.html", "w").write(src)
PY
gradle --no-daemon -q assembleRelease
OUT=app/build/outputs/apk/release/app-release.apk
echo "Built: $(pwd)/$OUT"
