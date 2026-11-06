# Re-capturing the "A" footage (product screen recordings)

The A clips are recorded by `tools/capture_demo.js`, which drives the real app with Playwright on clearly fictional **DEMO** data and burns a DEMO DATA label into every frame.
Nothing here touches real data: it needs a throwaway local Postgres and a local app server.

```
# 1. a local throwaway Postgres (example) and Playwright (already installed in the cloud environment)
# 2. run the capture (the reset script drops and recreates the throwaway DB between scenarios)
export DEMO_DB_ADMIN="postgresql://postgres@localhost:5433/postgres?host=/tmp" DEMO_DB_NAME=z2r_dev TOKEN_FILE=/tmp/e2e_token
andrew-builds/tools/reset_demo_env.sh
BASE=http://127.0.0.1:8099 RESET_CMD=andrew-builds/tools/reset_demo_env.sh TOKEN_FILE=$TOKEN_FILE \
  OUT=$PWD/andrew-builds/episode-001/screen-recordings/product-demo NODE_PATH=$(npm root -g) node andrew-builds/tools/capture_demo.js
```
Optional `TEST_VIDEO=<webm>` registers the browser-journey recording (`tests/e2e/journey.js`) as clip A11 (labelled AUTOMATED TEST RUN in the edit).

Each clip's `start_offset_s` (when the first real action begins) is written to `screen-recordings/product-demo/manifest.json` and used automatically by the edit.
Replace a clip with a **real-data** version by recording your own and naming it `EP001_<shot>_<slug>_<YYYYMMDD>_v02.<ext>`; the engine picks the highest-named file.
