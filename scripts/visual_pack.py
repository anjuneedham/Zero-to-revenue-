#!/usr/bin/env python3
"""Build a visual review pack (single HTML page) from a folder of markdown drafts.

Every [bracket] placeholder becomes a highlighted focus point with a checklist entry.
Usage: python3 scripts/visual_pack.py docs/master/ventures/agriloop/legal docs/visual/agriloop_legal_pack.html
"""
import html
import re
import sys
from pathlib import Path

DOCS = [
    ("BUSINESS_SUMMARY.md", "Business summary", "Give this to the lawyer first"),
    ("FOUNDER_AGREEMENT.md", "Founder agreement", "Share with your partner; fill in together"),
    ("TERMS_OF_USE.md", "Terms of use", "Shown at signup"),
    ("SELLER_AGREEMENT.md", "Seller agreement", "Shown before a first listing"),
    ("PRIVACY_POLICY.md", "Privacy policy", "Shown at signup"),
]
DECISION_WORDS = ("counsel", "founders", "choose", "confirm", "verify")
BRACKET = re.compile(r"\[([^\]\n]+)\]")


def is_decision(text):
    t = text.lower()
    return any(w in t for w in DECISION_WORDS)


class Doc:
    def __init__(self, idx):
        self.idx = idx
        self.points = []  # (id, kind, text)

    def mark(self, text):
        def sub(m):
            inner = m.group(1)
            kind = "decide" if is_decision(inner) else "fill"
            pid = f"d{self.idx}p{len(self.points) + 1}"
            self.points.append((pid, kind, inner))
            return f'<mark class="pt {kind}" id="{pid}" data-pid="{pid}">[{inner}]</mark>'
        return BRACKET.sub(sub, text)

    def inline(self, raw):
        s = html.escape(raw, quote=False)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        return self.mark(s)

    def render(self, md):
        out, in_ol, in_ul = [], False, False

        def close():
            nonlocal in_ol, in_ul
            if in_ol:
                out.append("</ol>")
            if in_ul:
                out.append("</ul>")
            in_ol = in_ul = False

        lines = md.splitlines()
        para = []

        def flush():
            if para:
                out.append(f"<p>{self.inline(' '.join(para))}</p>")
                para.clear()

        for line in lines:
            if not line.strip():
                flush()
                continue
            if line.startswith("# "):
                flush(); close()
                continue  # title is rendered by the section header
            if line.startswith("## "):
                flush(); close()
                out.append(f"<h3>{self.inline(line[3:])}</h3>")
                continue
            m = re.match(r"^(\d+)\.\s+(.*)", line)
            if m:
                flush()
                if not in_ol:
                    close(); out.append("<ol>"); in_ol = True
                para_text = m.group(2)
                out.append(f"<li>{self.inline(para_text)}")
                out.append("</li>")
                continue
            if line.startswith("- "):
                flush()
                if not in_ul:
                    close(); out.append("<ul>"); in_ul = True
                out.append(f"<li>{self.inline(line[2:])}</li>")
                continue
            if line.startswith("   ") and out and out[-1] == "</li>":
                out[-2] = out[-2] + " " + self.inline(line.strip())
                continue
            if line.startswith("  ") and in_ul and out and out[-1].endswith("</li>"):
                out[-1] = out[-1][:-5] + " " + self.inline(line.strip()) + "</li>"
                continue
            close()
            para.append(line.strip())
        flush(); close()
        return "\n".join(out)


CSS = """
:root{
  /* Layout: sticky document tabs over a single reading column; each document opens with its own focus-point checklist. */
  --bg:#F1F5F1; --surface:#FFFFFF; --ink:#15221A; --muted:#566860; --line:#D3DCD4;
  --brand:#1D6B45; --brand-ink:#FFFFFF;
  --fill-bg:#FFE27A; --fill-fg:#3A2D00; --dec-bg:#DCE8FF; --dec-fg:#102F66; --dec-line:#6C93D8;
  --done-bg:#D8EFE1; --done-fg:#1B5A3A;
  --display:'Bricolage Grotesque','Trebuchet MS',sans-serif; --body:'Source Sans 3','Segoe UI',sans-serif; --mono:'IBM Plex Mono',Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0F1712; --surface:#17231B; --ink:#E6EEE8; --muted:#9AB0A4; --line:#2B3C31;
  --brand:#5FC28D; --brand-ink:#0B1A11;
  --fill-bg:#6B5400; --fill-fg:#FFF2C2; --dec-bg:#1E3256; --dec-fg:#CFE0FF; --dec-line:#5C83C9;
  --done-bg:#1D4A33; --done-fg:#BDEBD0; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0F1712; --surface:#17231B; --ink:#E6EEE8; --muted:#9AB0A4; --line:#2B3C31;
  --brand:#5FC28D; --brand-ink:#0B1A11;
  --fill-bg:#6B5400; --fill-fg:#FFF2C2; --dec-bg:#1E3256; --dec-fg:#CFE0FF; --dec-line:#5C83C9;
  --done-bg:#1D4A33; --done-fg:#BDEBD0; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--body);font-size:17px;line-height:1.55;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px 64px}
.wrap{max-width:860px;margin:0 auto}
h1,h2,h3{font-family:var(--display);line-height:1.15;text-wrap:balance}
h1{font-size:clamp(28px,5vw,40px);margin:0 0 8px}
h2{font-size:26px;margin:0}
h3{font-size:19px;margin:26px 0 6px}
.banner{display:inline-block;font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;
  background:var(--fill-bg);color:var(--fill-fg);padding:4px 10px;border-radius:4px;margin-bottom:12px}
.lede{color:var(--muted);max-width:62ch;margin:0 0 18px}
.legend{display:flex;flex-wrap:wrap;gap:10px 18px;margin:0 0 18px;font-size:15px}
.legend span{display:flex;align-items:center;gap:8px}
.pt{font-family:var(--mono);font-size:.82em;padding:1px 6px;border-radius:4px;font-style:normal;cursor:pointer;scroll-margin-top:120px}
.pt.fill{background:var(--fill-bg);color:var(--fill-fg)}
.pt.decide{background:var(--dec-bg);color:var(--dec-fg);box-shadow:inset 0 0 0 1px var(--dec-line)}
.pt.done{background:var(--done-bg);color:var(--done-fg);box-shadow:none;text-decoration:line-through}
.total{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:18px}
.bar{height:10px;border-radius:5px;background:var(--line);overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;width:0;background:var(--brand);transition:width .25s}
nav{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);padding:8px 0;margin-bottom:10px;
  display:flex;gap:8px;overflow-x:auto;border-bottom:1px solid var(--line)}
nav a{white-space:nowrap;text-decoration:none;color:var(--ink);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:15px;background:var(--surface)}
nav a:focus-visible,.chk input:focus-visible{outline:3px solid var(--brand);outline-offset:2px}
nav a b{font-family:var(--mono);font-weight:500;font-size:12px;margin-left:6px;color:var(--muted)}
section.doc{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px clamp(16px,3vw,28px);margin:18px 0;scroll-margin-top:70px}
section.doc header p{margin:2px 0 0;color:var(--muted);font-size:15px}
.todo{border:1px dashed var(--line);border-radius:10px;padding:12px 14px;margin:16px 0}
.todo h4{margin:0 0 8px;font-family:var(--display);font-size:16px}
.chk{display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-top:1px solid var(--line)}
.chk:first-of-type{border-top:0}
.chk input{margin-top:5px;width:18px;height:18px;flex:none;accent-color:var(--brand)}
.chk label{min-width:0;overflow-wrap:anywhere}
.chk a{font-size:13px;margin-left:8px;color:var(--muted)}
.kind{font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-right:8px}
.doc ol,.doc ul{padding-left:1.3em}.doc li{margin:6px 0}
.none{color:var(--muted);font-size:15px;margin:0}
footer{margin-top:28px;color:var(--muted);font-size:14px}
@media (prefers-reduced-motion:reduce){.bar i{transition:none}}
"""

JS = """
(function(){
  var KEY='agriloop-legal-pack-v1',done={};
  try{done=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
  var boxes=[].slice.call(document.querySelectorAll('.chk input'));
  function save(){try{localStorage.setItem(KEY,JSON.stringify(done))}catch(e){}}
  function paint(){
    var n=0;
    boxes.forEach(function(b){
      var id=b.dataset.pid,on=!!done[id];b.checked=on;if(on)n++;
      [].slice.call(document.querySelectorAll('[data-pid="'+id+'"]')).forEach(function(m){if(m.tagName==='MARK')m.classList.toggle('done',on)});
    });
    document.getElementById('count').textContent=n+' of '+boxes.length+' focus points done';
    document.querySelector('.bar i').style.width=(boxes.length?100*n/boxes.length:0)+'%';
    [].slice.call(document.querySelectorAll('nav a')).forEach(function(a){
      var d=a.dataset.doc,t=0,c=0;boxes.forEach(function(b){if(b.dataset.doc===d){t++;if(done[b.dataset.pid])c++}});
      a.querySelector('b').textContent=c+'/'+t;
    });
  }
  boxes.forEach(function(b){b.addEventListener('change',function(){done[b.dataset.pid]=b.checked;save();paint()})});
  [].slice.call(document.querySelectorAll('mark.pt')).forEach(function(m){m.addEventListener('click',function(){done[m.dataset.pid]=!done[m.dataset.pid];save();paint()})});
  paint();
})();
"""


def build(src_dir, out_path):
    src = Path(src_dir)
    sections, nav, total = [], [], 0
    for i, (fname, title, note) in enumerate(DOCS, 1):
        md = (src / fname).read_text()
        d = Doc(i)
        body = d.render(md)
        total += len(d.points)
        items = "".join(
            f'<div class="chk"><input type="checkbox" id="c-{pid}" data-pid="{pid}" data-doc="doc{i}">'
            f'<label for="c-{pid}"><span class="kind">{"Decide" if k == "decide" else "Fill in"}</span>{html.escape(t)}'
            f'<a href="#{pid}">see in text</a></label></div>'
            for pid, k, t in d.points
        )
        todo = (f'<div class="todo"><h4>What to update and check ({len(d.points)})</h4>{items}</div>'
                if d.points else '<div class="todo"><h4>What to update and check</h4><p class="none">Nothing to fill in. Read it once and change anything that does not match how you operate.</p></div>')
        sections.append(
            f'<section class="doc" id="doc{i}"><header><h2>{html.escape(title)}</h2><p>{html.escape(note)}</p></header>{todo}{body}</section>'
        )
        nav.append(f'<a href="#doc{i}" data-doc="doc{i}">{html.escape(title)}<b>0/{len(d.points)}</b></a>')
    page = f"""<title>Agriloop Legal Pack</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700&family=IBM+Plex+Mono:wght@400;500&family=Source+Sans+3:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<span class="banner">Draft. Not legal advice.</span>
<h1>Agriloop Legal Pack</h1>
<p class="lede">Five drafts for the founding beta. Everything you must fill in or decide is highlighted. Tap a highlight, or tick it in the checklist, once you have dealt with it.</p>
<div class="legend">
<span><mark class="pt fill">[fill in]</mark> a fact only you know</span>
<span><mark class="pt decide">[decide]</mark> a choice for you and your partner, or a point for the lawyer</span>
</div>
<div class="total"><strong id="count"></strong><div class="bar"><i></i></div></div>
<nav aria-label="Documents">{''.join(nav)}</nav>
{''.join(sections)}
<footer>Launch rules these drafts assume: invite-only beta, free for 60 days, cash and invoice orders only, no card payments and no held funds until the legal review is finished (target: end of November). Source files: <code>docs/master/ventures/agriloop/legal/</code>. Rebuild with <code>scripts/visual_pack.py</code>.</footer>
</div>
<script>{JS}</script>
"""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(page)
    return total


if __name__ == "__main__":
    n = build(sys.argv[1], sys.argv[2])
    print(f"built {sys.argv[2]} with {n} focus points")
