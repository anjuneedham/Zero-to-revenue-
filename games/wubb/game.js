(function () {
  "use strict";
  var T = 32, ROWS = 14, W = 800, H = 448;
  var canvas = document.getElementById("c");
  var ctx = canvas.getContext("2d");

  // ---------- fit to screen ----------
  function resize() {
    var s = Math.min(window.innerWidth / W, window.innerHeight / H);
    canvas.style.width = Math.floor(W * s) + "px";
    canvas.style.height = Math.floor(H * s) + "px";
  }
  window.addEventListener("resize", resize);
  resize();
  var isTouch = "ontouchstart" in window || navigator.maxTouchPoints > 0;
  if (isTouch) document.body.classList.add("touch");

  // ---------- audio (tiny synth) ----------
  var actx = null;
  function beep(freq, dur, type, slide) {
    try {
      if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
      var o = actx.createOscillator(), g = actx.createGain();
      o.type = type || "square";
      o.frequency.value = freq;
      if (slide) o.frequency.linearRampToValueAtTime(freq + slide, actx.currentTime + dur);
      g.gain.value = 0.06;
      g.gain.exponentialRampToValueAtTime(0.0001, actx.currentTime + dur);
      o.connect(g); g.connect(actx.destination);
      o.start(); o.stop(actx.currentTime + dur);
    } catch (e) {}
  }
  var sfx = {
    jump: function () { beep(380, 0.14, "square", 280); },
    star: function () { beep(880, 0.08, "triangle"); setTimeout(function () { beep(1320, 0.12, "triangle"); }, 70); },
    stomp: function () { beep(220, 0.15, "sawtooth", -120); },
    oops: function () { beep(300, 0.3, "sawtooth", -220); },
    win: function () { [523, 659, 784, 1047].forEach(function (f, i) { setTimeout(function () { beep(f, 0.2, "triangle"); }, i * 120); }); }
  };

  // ---------- input ----------
  var keys = {}, touch = { left: false, right: false, jump: false };
  window.addEventListener("keydown", function (e) {
    if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", " "].indexOf(e.key) >= 0) e.preventDefault();
    keys[e.key.toLowerCase()] = true;
    onPress(e.key.toLowerCase());
  });
  window.addEventListener("keyup", function (e) { keys[e.key.toLowerCase()] = false; });
  function bindBtn(id, name) {
    var el = document.getElementById(id);
    function on(e) { e.preventDefault(); touch[name] = true; el.classList.add("on"); onPress("touch"); }
    function off(e) { e.preventDefault(); touch[name] = false; el.classList.remove("on"); }
    el.addEventListener("pointerdown", on);
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (n) { el.addEventListener(n, off); });
  }
  bindBtn("bl", "left"); bindBtn("br", "right"); bindBtn("bj", "jump");
  canvas.addEventListener("pointerdown", function () { onPress("touch"); });

  // ---------- state ----------
  var state = "title", players = 1, levelIdx = 0, L, grid, P = [], enemies = [], stars = [], camX = 0, tAnim = 0;
  var best = {};
  try { best = JSON.parse(localStorage.getItem("wubb-best") || "{}"); } catch (e) {}
  function saveBest() { try { localStorage.setItem("wubb-best", JSON.stringify(best)); } catch (e) {} }

  function onPress(k) {
    if (state === "title") {
      if (k === "1") { players = 1; startLevel(0); }
      else if (k === "2") { players = 2; startLevel(0); }
      else if (k === "enter" || k === " " || k === "touch") { players = k === "touch" ? 1 : players; startLevel(0); }
      else if (k === "arrowleft" || k === "arrowright") { players = players === 1 ? 2 : 1; }
    } else if (state === "done") {
      if (k === "enter" || k === " " || k === "touch") {
        if (levelIdx + 1 < LEVELS.length) startLevel(levelIdx + 1); else state = "title";
      }
    }
  }

  function startLevel(i) {
    levelIdx = i; L = LEVELS[i];
    grid = [];
    for (var y = 0; y < ROWS; y++) { var row = []; for (var x = 0; x < L.w; x++) row.push(y >= 12 ? "#" : " "); grid.push(row); }
    L.gaps.forEach(function (g) { for (var x = g[0]; x < g[1]; x++) { grid[12][x] = " "; grid[13][x] = " "; } });
    L.plats.forEach(function (p) { for (var x = p[0]; x < p[0] + p[2]; x++) grid[p[1]][x] = "="; });
    stars = L.stars.map(function (s) { return { x: s[0] * T + 16, y: s[1] * T + 16, got: false }; });
    enemies = L.enemies.map(function (e) {
      return { x: e[0] * T, y: e[1] * T + T - 26, w: 28, h: 26, dir: 1, minX: (e[0] - e[2]) * T, maxX: (e[0] + e[2]) * T, dead: 0 };
    });
    P = [];
    for (var n = 0; n < players; n++) P.push(makePlayer(n));
    camX = 0; state = "play";
  }

  function makePlayer(n) {
    return { id: n, x: 2 * T + n * 36, y: 10 * T, vx: 0, vy: 0, w: 22, h: 28, on: false, coyote: 0, buf: 0, face: 1,
      inv: 0, safeX: 2 * T + n * 36, safeY: 10 * T, wasJump: false, color: n === 0 ? ["#ffd93b", "#ff9f1c"] : ["#6ee7b7", "#0ea5a5"] };
  }

  // ---------- tiles ----------
  function tileAt(tx, ty) {
    if (tx < 0 || tx >= L.w) return "#";
    if (ty < 0 || ty >= ROWS) return " ";
    return grid[ty][tx];
  }

  function controls(p) {
    var left, right, jump;
    if (players === 1) {
      left = keys["a"] || keys["arrowleft"] || touch.left;
      right = keys["d"] || keys["arrowright"] || touch.right;
      jump = keys["w"] || keys["arrowup"] || keys[" "] || touch.jump;
    } else if (p.id === 0) {
      left = keys["a"]; right = keys["d"]; jump = keys["w"] || keys[" "] || touch.jump;
      left = left || touch.left; right = right || touch.right;
    } else {
      left = keys["arrowleft"]; right = keys["arrowright"]; jump = keys["arrowup"];
    }
    return { left: !!left, right: !!right, jump: !!jump };
  }

  function hurt(p) {
    sfx.oops();
    p.x = p.safeX; p.y = p.safeY - 4; p.vx = p.vy = 0; p.inv = 1.2;
  }

  function overlap(a, b) { return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }

  function updatePlayer(p, dt) {
    var c = controls(p);
    var target = (c.right ? 1 : 0) - (c.left ? 1 : 0);
    if (target) p.face = target;
    var accel = p.on ? 1800 : 1100;
    p.vx += (target * 230 - p.vx) * Math.min(1, accel * dt / 230);
    if (!target && Math.abs(p.vx) < 8) p.vx = 0;

    if (c.jump && !p.wasJump) p.buf = 0.12;
    p.wasJump = c.jump;
    p.buf -= dt;
    p.coyote -= dt;
    if (p.buf > 0 && p.coyote > 0) { p.vy = -610; p.buf = 0; p.coyote = 0; p.on = false; sfx.jump(); }
    if (!c.jump && p.vy < -220) p.vy = -220; // short hop when released early
    p.vy = Math.min(p.vy + 1700 * dt, 900);

    // X axis (solid blocks only)
    p.x += p.vx * dt;
    var ty0 = Math.floor(p.y / T), ty1 = Math.floor((p.y + p.h - 0.01) / T), tx, ty;
    if (p.vx > 0) {
      tx = Math.floor((p.x + p.w) / T);
      for (ty = ty0; ty <= ty1; ty++) if (tileAt(tx, ty) === "#") { p.x = tx * T - p.w; p.vx = 0; break; }
    } else if (p.vx < 0) {
      tx = Math.floor(p.x / T);
      for (ty = ty0; ty <= ty1; ty++) if (tileAt(tx, ty) === "#") { p.x = (tx + 1) * T; p.vx = 0; break; }
    }
    // keep inside the screen in co-op, and inside the world always
    var minX = Math.max(0, camX), maxX = Math.min(L.w * T, camX + W) - p.w;
    if (p.x < minX) { p.x = minX; p.vx = Math.max(p.vx, 0); }
    if (p.x > maxX) { p.x = maxX; p.vx = Math.min(p.vx, 0); }

    // Y axis (solid + one-way platforms)
    var prevBottom = p.y + p.h;
    p.y += p.vy * dt;
    p.on = false;
    var tx0 = Math.floor(p.x / T), tx1 = Math.floor((p.x + p.w - 0.01) / T);
    if (p.vy >= 0) {
      ty = Math.floor((p.y + p.h) / T);
      for (tx = tx0; tx <= tx1; tx++) {
        var t = tileAt(tx, ty);
        if (t === "#" || (t === "=" && prevBottom <= ty * T + 1)) { p.y = ty * T - p.h; p.vy = 0; p.on = true; break; }
      }
    } else {
      ty = Math.floor(p.y / T);
      for (tx = tx0; tx <= tx1; tx++) if (tileAt(tx, ty) === "#") { p.y = (ty + 1) * T; p.vy = 0; break; }
    }
    if (p.on) {
      p.coyote = 0.1;
      var fx = Math.floor((p.x + p.w / 2) / T), below = Math.floor((p.y + p.h + 1) / T);
      if (tileAt(fx, below) === "#" && tileAt(Math.floor(p.x / T), below) === "#" && tileAt(Math.floor((p.x + p.w) / T), below) === "#") {
        p.safeX = p.x; p.safeY = p.y;
      }
    }
    if (p.y > H + 60) hurt(p);
    if (p.inv > 0) p.inv -= dt;

    // stars
    stars.forEach(function (s) {
      if (!s.got && Math.abs(p.x + p.w / 2 - s.x) < 22 && Math.abs(p.y + p.h / 2 - s.y) < 26) { s.got = true; sfx.star(); }
    });
    // enemies
    enemies.forEach(function (e) {
      if (e.dead || !overlap(p, e)) return;
      if (p.vy > 0 && p.y + p.h - e.y < 18) { e.dead = 0.35; p.vy = -420; sfx.stomp(); }
      else if (p.inv <= 0) hurt(p);
    });
    // spikes
    if (p.inv <= 0) L.spikes.forEach(function (sx) {
      if (overlap(p, { x: sx * T + 6, y: 11 * T + 16, w: 20, h: 16 })) hurt(p);
    });
  }

  function update(dt) {
    tAnim += dt;
    if (state !== "play") return;
    var cx = 0; P.forEach(function (p) { cx += p.x + p.w / 2; }); cx /= P.length;
    var target = Math.max(0, Math.min(L.w * T - W, cx - W / 2));
    camX += (target - camX) * Math.min(1, dt * 8);
    P.forEach(function (p) { updatePlayer(p, dt); });
    enemies.forEach(function (e) {
      if (e.dead) { e.dead -= dt; return; }
      e.x += e.dir * 55 * dt;
      if (e.x < e.minX) { e.x = e.minX; e.dir = 1; }
      if (e.x > e.maxX) { e.x = e.maxX; e.dir = -1; }
    });
    var goal = { x: L.goal * T, y: 8 * T, w: T, h: 4 * T };
    if (P.some(function (p) { return overlap(p, goal); })) {
      var got = stars.filter(function (s) { return s.got; }).length;
      best[levelIdx] = Math.max(best[levelIdx] || 0, got); saveBest();
      state = "done"; sfx.win();
    }
  }

  // ---------- drawing ----------
  function rr(x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  function drawBackdrop() {
    var g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, L.sky[0]); g.addColorStop(1, L.sky[1]);
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = L.hill;
    for (var layer = 0; layer < 2; layer++) {
      var off = camX * (0.2 + layer * 0.2);
      ctx.beginPath(); ctx.moveTo(0, H);
      for (var x = 0; x <= W; x += 20) ctx.lineTo(x, 300 + layer * 30 + Math.sin((x + off) / (70 + layer * 40)) * 26);
      ctx.lineTo(W, H); ctx.closePath(); ctx.globalAlpha = 0.55 + layer * 0.25; ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = "rgba(255,255,255,.8)";
    for (var i = 0; i < 6; i++) {
      var cx = ((i * 230 - camX * 0.3 + tAnim * 6) % (W + 200) + W + 200) % (W + 200) - 100, cy = 50 + (i % 3) * 38;
      ctx.beginPath(); ctx.arc(cx, cy, 22, 0, 7); ctx.arc(cx + 24, cy + 4, 18, 0, 7); ctx.arc(cx - 22, cy + 6, 16, 0, 7); ctx.fill();
    }
  }

  function drawTiles() {
    var x0 = Math.floor(camX / T), x1 = Math.min(L.w - 1, x0 + W / T + 1);
    for (var y = 0; y < ROWS; y++) for (var x = x0; x <= x1; x++) {
      var t = grid[y][x], px = x * T, py = y * T;
      if (t === "#") {
        ctx.fillStyle = L.dirt; ctx.fillRect(px, py, T, T);
        if (y === 12 || grid[y - 1][x] !== "#") { ctx.fillStyle = L.ground; ctx.fillRect(px, py, T, 9); }
      } else if (t === "=") {
        ctx.fillStyle = L.ground; rr(px, py, T, 14, 5); ctx.fill();
        ctx.fillStyle = "rgba(255,255,255,.35)"; ctx.fillRect(px + 3, py + 2, T - 6, 3);
      }
    }
    L.spikes.forEach(function (sx) {
      ctx.fillStyle = "#e5e7eb"; ctx.beginPath();
      ctx.moveTo(sx * T + 3, 12 * T); ctx.lineTo(sx * T + 16, 11 * T + 12); ctx.lineTo(sx * T + 29, 12 * T); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#6b7280"; ctx.lineWidth = 2; ctx.stroke();
    });
    // goal flag
    var gx = L.goal * T + 8;
    ctx.fillStyle = "#fff"; ctx.fillRect(gx, 8 * T, 5, 4 * T);
    var cols = ["#ef4444", "#f59e0b", "#22c55e", "#3b82f6"];
    for (var i = 0; i < 4; i++) { ctx.fillStyle = cols[i]; ctx.fillRect(gx + 5, 8 * T + i * 11 + Math.sin(tAnim * 5 + i) * 2, 32, 11); }
  }

  function star(x, y, r, rot) {
    ctx.beginPath();
    for (var i = 0; i < 10; i++) {
      var a = rot + i * Math.PI / 5 - Math.PI / 2, rad = i % 2 ? r * 0.45 : r;
      ctx.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad);
    }
    ctx.closePath(); ctx.fill();
  }

  function drawStars() {
    stars.forEach(function (s, i) {
      if (s.got) return;
      var bob = Math.sin(tAnim * 4 + i) * 3;
      ctx.fillStyle = "#fff6a8"; star(s.x, s.y + bob, 13, 0);
      ctx.fillStyle = "#ffd400"; star(s.x, s.y + bob, 10, Math.sin(tAnim * 3 + i) * 0.15);
    });
  }

  function drawEnemies() {
    enemies.forEach(function (e) {
      var sq = e.dead ? 0.4 : 1, h = e.h * sq, y = e.y + e.h - h;
      ctx.fillStyle = "#8b5cf6"; rr(e.x, y, e.w, h, 10); ctx.fill();
      if (e.dead) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(e.x + 6, y + 6, 6, 8); ctx.fillRect(e.x + 16, y + 6, 6, 8);
      ctx.fillStyle = "#111"; var dx = e.dir * 1.5; ctx.fillRect(e.x + 8 + dx, y + 9, 3, 5); ctx.fillRect(e.x + 18 + dx, y + 9, 3, 5);
      ctx.strokeStyle = "#311"; ctx.lineWidth = 2; ctx.beginPath();
      ctx.moveTo(e.x + 5, y + 4); ctx.lineTo(e.x + 12, y + 7); ctx.moveTo(e.x + 23, y + 4); ctx.lineTo(e.x + 16, y + 7); ctx.stroke();
    });
  }

  function drawPlayer(p) {
    if (p.inv > 0 && Math.floor(p.inv * 12) % 2) return;
    var cx = p.x + p.w / 2, f = p.face, run = Math.abs(p.vx) > 20 && p.on ? Math.sin(tAnim * 22) * 2 : 0;
    // curly tail
    ctx.strokeStyle = p.color[1]; ctx.lineWidth = 4; ctx.lineCap = "round"; ctx.beginPath();
    ctx.moveTo(cx - f * 9, p.y + 20);
    ctx.bezierCurveTo(cx - f * 22, p.y + 16, cx - f * 18, p.y + 2 + run, cx - f * 12, p.y + 6);
    ctx.stroke();
    // body
    ctx.fillStyle = p.color[0]; rr(p.x, p.y + 2, p.w, p.h - 2, 9); ctx.fill();
    ctx.strokeStyle = p.color[1]; ctx.lineWidth = 2; ctx.stroke();
    // eyes
    ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(cx - 5 + f * 2, p.y + 11, 5, 0, 7); ctx.arc(cx + 5 + f * 2, p.y + 11, 5, 0, 7); ctx.fill();
    ctx.fillStyle = "#111"; ctx.beginPath(); ctx.arc(cx - 4 + f * 3, p.y + 12, 2.4, 0, 7); ctx.arc(cx + 6 + f * 3, p.y + 12, 2.4, 0, 7); ctx.fill();
    // smile
    ctx.strokeStyle = "#7c2d12"; ctx.lineWidth = 1.8; ctx.beginPath(); ctx.arc(cx + f * 2, p.y + 17, 4, 0.15 * Math.PI, 0.85 * Math.PI); ctx.stroke();
    // feet
    ctx.fillStyle = p.color[1];
    ctx.fillRect(p.x + 2 + run, p.y + p.h - 3, 7, 4); ctx.fillRect(p.x + p.w - 9 - run, p.y + p.h - 3, 7, 4);
  }

  function text(s, x, y, size, color, align) {
    ctx.font = "bold " + size + "px 'Trebuchet MS',system-ui,sans-serif";
    ctx.textAlign = align || "center"; ctx.lineJoin = "round"; ctx.lineWidth = size / 6; ctx.strokeStyle = "rgba(0,0,0,.45)";
    ctx.strokeText(s, x, y); ctx.fillStyle = color || "#fff"; ctx.fillText(s, x, y);
  }

  function drawHud() {
    var got = stars.filter(function (s) { return s.got; }).length;
    ctx.fillStyle = "#ffd400"; star(28, 28, 13, 0);
    text(got + " / " + stars.length, 52, 36, 22, "#fff", "left");
    text(L.name, W - 16, 34, 20, "#fff", "right");
  }

  function drawTitle() {
    L = LEVELS[0]; camX = 0; grid = grid || [];
    var g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, "#8fe3ff"); g.addColorStop(1, "#d8f6ff");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#7fdc8a"; ctx.beginPath(); ctx.moveTo(0, H);
    for (var x = 0; x <= W; x += 20) ctx.lineTo(x, 330 + Math.sin(x / 60 + tAnim) * 16);
    ctx.lineTo(W, H); ctx.fill();
    ctx.fillStyle = "#5bbf5b"; ctx.fillRect(0, 400, W, 48);
    for (var i = 0; i < 8; i++) { ctx.fillStyle = "#ffd400"; star(70 + i * 95, 80 + Math.sin(tAnim * 3 + i) * 10, 14, tAnim * 0.5 + i); }
    text("Wow! Wubb Adventure", W / 2, 150, 56, "#fff");
    text("a fan-made tribute for two", W / 2, 188, 20, "#fff");
    var a = makePlayer(0), b = makePlayer(1);
    a.x = W / 2 - 60; a.y = 330; a.face = 1; b.x = W / 2 + 40; b.y = 330; b.face = -1;
    a.inv = 0; b.inv = 0; tAnimJump(a, 0); tAnimJump(b, 1.5);
    drawPlayer(a); if (players === 2) drawPlayer(b);
    text(players === 1 ? "◀  1 PLAYER  ▶" : "◀  2 PLAYERS  ▶", W / 2, 256, 30, "#fff");
    var hint = isTouch ? "Tap to start" : "Press Enter to start  (1 or 2 to pick players)";
    text(hint, W / 2, 292, 20, "#fff");
    if (!isTouch) text(players === 1 ? "Move: A/D or ←/→   Jump: W, ↑ or Space" : "P1: A/D + W      P2: ←/→ + ↑", W / 2, 424, 18, "#fff");
  }
  function tAnimJump(p, ph) { p.y -= Math.abs(Math.sin(tAnim * 4 + ph)) * 26; }

  function drawDone() {
    ctx.fillStyle = "rgba(20,20,60,.55)"; ctx.fillRect(0, 0, W, H);
    var got = stars.filter(function (s) { return s.got; }).length, last = levelIdx + 1 >= LEVELS.length;
    text(last ? "You did it! 🎉" : "Wow! Level clear!", W / 2, 170, 52, "#fff");
    text("Stars: " + got + " / " + stars.length + "   (best " + (best[levelIdx] || got) + ")", W / 2, 224, 28, "#ffd400");
    text(isTouch ? "Tap to continue" : "Press Enter to continue", W / 2, 280, 22, "#fff");
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    if (state === "title") { drawTitle(); return; }
    drawBackdrop();
    ctx.save(); ctx.translate(-Math.round(camX), 0);
    drawTiles(); drawStars(); drawEnemies(); P.forEach(drawPlayer);
    ctx.restore();
    drawHud();
    if (state === "done") drawDone();
  }

  var last = 0;
  function frame(t) {
    var dt = Math.min(0.033, (t - last) / 1000 || 0); last = t;
    update(dt); draw(); requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // test hook
  window.__wubb = { get state() { return state; }, get players() { return P; }, startLevel: startLevel, keys: keys };
})();
