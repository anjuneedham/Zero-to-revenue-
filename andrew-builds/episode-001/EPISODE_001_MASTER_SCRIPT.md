# EPISODE 001: MASTER SCRIPT

**Title:** I'm Building a Business From Scratch (And Building the Software to Run It)
**Alternative:** Can I Build a Business Using Software I'm Building Myself?
**Channel:** Andrew Builds · **Format:** long-form documentary, voiceover over real screen recordings and desk footage.

*Generated from `editing-project/episode_001.json` by `tools/make_docs.py`. Edit the JSON, not this file.*

## Status: DRAFT, WAITING FOR YOUR INPUT
Every spoken word is written. Anything I could not verify is a **bracketed placeholder**, never an invented fact:

| Marker | Meaning |
|---|---|
| `[FILL: ...]` | A fact only you know (a number, your reason, your offer). Replace the whole bracket with what you will say. |
| `[RECORD: ...]` | A moment only you can describe, in your own words, and only if it really happened. |

Until the placeholders are filled, any render is an **assembly proof** and is watermarked as such.

## Length
| Section | Plan | Own words | Placeholders | Est. read time |
|---|---|---|---|---|
| VO_001_HOOK | 0:00-0:40 | 117 | 1 | 0:55 |
| VO_002_BACKGROUND | 0:40-2:00 | 199 | 2 | 1:32 |
| VO_003_BUSINESS | 2:00-3:30 | 156 | 4 | 1:23 |
| VO_004_SOFTWARE | 3:30-5:30 | 326 | 1 | 2:20 |
| VO_005_EXECUTION | 5:30-7:30 | 255 | 2 | 1:57 |
| VO_006_OPPORTUNITY | 7:30-9:00 | 231 | 0 | 1:37 |
| VO_007_CLOSING | 9:00-11:30 | 213 | 2 | 1:39 |
| **Total** | 0:00-11:30 | **1497** | **12** | **11:24** |

**Runtime, honestly:** the script has 1497 words of its own. At a relaxed 150 words per minute that is about 10:22 before your placeholders; each filled placeholder adds
roughly 10-30 spoken words. So the finished voiceover should land near **11:24**. That is an **estimate**: a fast reader (160+ wpm) who answers each placeholder in one short phrase could finish
just under 10:00. If that happens, add a real example or detail to one of the placeholders (Scene 3 or Scene 5 are the best places); do not pad. The actual length is confirmed only after you record.
The robot guide track for the whole script measured 9:24 with every placeholder spoken as a short pause.

## Claims check (what each factual statement rests on)
| Statement in the script | Source |
|---|---|
| Years of sales and customer service; ran own businesses, helped others run theirs; uses AI to build websites, funnels, apps | `docs/strategy/OWNER_PROFILE.md` (owner-provided 25 Oct 2026) |
| An earlier system found "over a hundred" qualified opportunities; verified revenue "at the time: zero" | `docs/FOUNDERS_LOG.md` 26 Oct 2026 (121 qualified, $0 verified). **Confirm it is still zero when you record.** |
| A business-contact database does not cover small local trades | `docs/FOUNDERS_LOG.md` 26 Oct 2026 (Clay) |
| Ten or fifteen real contacts as the first test | `docs/FOUNDERS_LOG.md` 26 Oct 2026 |
| Twelve editable playbooks; Today screen; pipeline; step-through history; counts instead of percentages; no AI; does not send messages | The shipped product; see `project-documentation/PRODUCT_TEST_REPORT.md` |
| "Tested the whole journey in a browser on made-up businesses" | `tests/e2e/journey.js`: 25 checks run and passed on 6 Nov 2026 |
| "Exactly one user: me. Zero customers for the software." | True as far as any repo shows. **Confirm.** |

Deliberately **not** claimed: any revenue, any number of replies or customers, product-market fit, any AI capability, any price.

---

### Scene 1 - Cold open

**SCENE:** Scene 1 - Cold open  (file `VO_001_HOOK.wav`)

**PURPOSE:** Hook the viewer with the premise: starting now, with two experiments in one. Show real work immediately.

**ESTIMATED DURATION:** plan 0:00-0:40 · estimated from the text: 0:55 (117 own words + 1 placeholder(s)). The real length is whatever you record; the edit adapts to it.

**VOICEOVER:**

> What if I stopped waiting for the perfect idea? The perfect software. The perfect moment.
>
> What if I just started?
>
> I already have. I've begun reaching out to businesses, [FILL: how many, in a short phrase, e.g. "a few dozen"] so far, and I'm trying to turn those conversations into paying customers.
>
> But there's a second experiment hiding inside the first.
>
> I'm also building the software I use to run all of it. The pipeline. The follow-ups. The playbooks. Every step I take, tracked in a tool that I'm writing while I use it.
>
> If it works, I could end up with two businesses out of one experiment. If it doesn't, you'll get to watch me find out why.
>
> I'm Andrew. This is the Bootstrapper Experiment. Episode one.

**VISUALS:** Fast, silent-feeling montage cut to the voice: the Today screen, the pipeline, a playbook running, the real outreach moment, desk and tablet. End on a title card.

**SCREEN RECORDING:** A05, A09, A03 (captured). B02 and B06 (yours). Use real outreach footage first if you have it.

**EDITING NOTES:** Cut on the sentence breaks, not faster. No music for the first two lines, then bring the bed in under 'I already have.' Title card 'BOOTSTRAPPER EXPERIMENT / EPISODE 001' for the final 3 seconds.

**TRANSITION TO NEXT SCENE:** Hard cut to a calmer, slower shot of you at your desk for the background scene.

### Scene 2 - The background

**SCENE:** Scene 2 - The background  (file `VO_002_BACKGROUND.wav`)

**PURPOSE:** Say who you are and why you're doing this, briefly, and set honest stakes.

**ESTIMATED DURATION:** plan 0:40-2:00 · estimated from the text: 1:32 (199 own words + 2 placeholder(s)). The real length is whatever you record; the edit adapts to it.

**VOICEOVER:**

> Quick background, and I'll keep it short.
>
> I've spent years in sales and customer service. I've run my own businesses, and I've helped other people run theirs. [FILL: one sentence in your own words about your marketing, growth or business-development work.] These days, a lot of what I do is use AI to build websites, funnels and small apps that solve a specific problem.
>
> Here's what I've learned from all of that. Building is the easy part now. The hard part is the thing nobody films: getting the first people to say yes.
>
> I'm not saying that to sound clever. I can get a working page or app live much faster than I used to. Getting someone to care about it hasn't got any faster at all.
>
> About two weeks ago I built a system that went out and found opportunities for me. It found over a hundred that it called qualified. Verified revenue from that system, at the time? Zero.
>
> Those two numbers, side by side, taught me more than any course. A big list looks like progress. It isn't.
>
> So I'm doing this differently. [FILL: why you want to bootstrap, in your own words. For example: no investors, no safety net, a preference for proof over pitch decks. Only say what's true for you.]
>
> And I'm doing it in public, because a story with only the wins in it isn't useful to anyone. You'll see the numbers. Including the bad ones.

**VISUALS:** You to camera or at your desk if you have it. Otherwise slow B-roll of your workspace and the tablet, then the Treasury/verified-revenue screen for the 'zero' line.

**SCREEN RECORDING:** B06, B07 (yours). B08 dev environment (yours). Optional: your own Treasury page showing $0 verified, only if still true on the recording day.

**EDITING NOTES:** Let this breathe. No cut faster than ~4 seconds. A single lower-third on the first sentence ('Sales - Customer service - Own businesses'). On 'Zero.' hold on a plain frame, then music out.

**TRANSITION TO NEXT SCENE:** Dip to black for 0.3s, then into the pipeline screen.

### Scene 3 - The business

**SCENE:** Scene 3 - The business  (file `VO_003_BUSINESS.wav`)

**PURPOSE:** Say exactly what you're selling, to whom, how you're finding them, and the real status.

**ESTIMATED DURATION:** plan 2:00-3:30 · estimated from the text: 1:23 (156 own words + 4 placeholder(s)). The real length is whatever you record; the edit adapts to it.

**VOICEOVER:**

> So what's the actual business?
>
> [FILL: the offer in one plain sentence. Options in the project notes: a contractor-focused app called BuildFlow, done-for-you website and funnel setup, or a monthly growth-plan retainer. Say only what you are really selling.]
>
> The customers are [FILL: who exactly. The notes point to small trades and contracting businesses in Jamaica. Confirm or correct this.]
>
> How do I find them? Not the way I first tried. I tested a proper business-contact database, and it simply doesn't cover small local trades. So I'm starting where the real conversations are: businesses I can see, people I know, and people I can be introduced to.
>
> The plan from the start was simple. Pick a small group of real contacts, send a real message to each, and watch what happens. Not a thousand emails. Ten or fifteen honest ones.
>
> I know ten or fifteen conversations won't prove a business. They're a first sample. What they will tell me is whether people answer at all, which words get a reply, and where I get stuck. Right now that's worth more than a big list.
>
> [FILL: the real status in one or two sentences. How many you've contacted, how many replied, whether anyone has agreed to a call. If the answer is "no replies yet," say exactly that.]
>
> I want to be clear about one thing. As I record this, [FILL: your verified revenue, or "I haven't made a dollar from this yet"]. When that changes, you'll see the proof, not just the claim.

**VISUALS:** Your real pipeline (names blurred), the real message composer (recipient hidden), then the Insights counts.

**SCREEN RECORDING:** B01 and B04 (yours, after you back-fill). A09 as a stand-in only if clearly labelled DEMO DATA.

**EDITING NOTES:** Blur or crop every name, number and handle. On the status line, cut to the plain counts (no zoom-ins, no graphics that make a small number look big).

**TRANSITION TO NEXT SCENE:** Slide from the pipeline list into the Today screen.

### Scene 4 - The software

**SCENE:** Scene 4 - The software  (file `VO_004_SOFTWARE.wav`)

**PURPOSE:** Show the product honestly: the problem, what it does, what it deliberately does not do.

**ESTIMATED DURATION:** plan 3:30-5:30 · estimated from the text: 2:20 (326 own words + 1 placeholder(s)). The real length is whatever you record; the edit adapts to it.

**VOICEOVER:**

> Now the software, because this is where it gets interesting.
>
> When you do outreach, the work isn't just sending messages. It's remembering. Who did I contact? What did I say? Did they reply? When should I follow up? Which message actually worked?
>
> If that lives in your head, or scattered across notes and chats, you can't learn anything from it. You just repeat yourself and hope.
>
> So I'm building the tool I wish I had. It has a Today screen that tells me what to do first: who's due for a follow-up, who replied, and who's going nowhere. It has a pipeline, so every business sits at a clear stage, from just found, to customer, or lost. And it has playbooks.
>
> Every task has a priority and a due date, and every task points back to the business it belongs to. So Today isn't a wall of notes. It's a short list I can actually finish. I set daily targets, like five prospects researched and five first messages, and I can change them whenever they stop making sense.
>
> A playbook is a set of steps for one job. Researching a prospect. Writing a first message. Following up. Handling an objection. There are twelve to start with, and they're fully editable, because my offer won't be your offer.
>
> Everything I do gets logged. Open any business and you can step through its history, event by event, to see exactly what happened. Nothing gets quietly rewritten.
>
> And the reports are deliberately honest. If I've sent six messages and one got a reply, it shows one of six. Not seventeen percent. Six isn't enough to say anything.
>
> What it doesn't do: it doesn't send messages for me, and it doesn't pretend to be smart. There's no AI judge in there. It records what I do, and it shows me what I recorded.
>
> I've tested the whole journey, from first note to closed deal, in a browser, on made-up businesses. [FILL: if true by recording day, say "Now it's being used on my real ones."]

**VISUALS:** Screen recordings of the actual product, in the order of the narration: Today, pipeline, playbooks, timeline playback, insights. Every demo clip carries a DEMO DATA label burned in.

**SCREEN RECORDING:** A01, A05, A09, A03, A08, A06, A07, A11 (all captured by me, DEMO DATA).

**EDITING NOTES:** One highlight box per shot, on the thing being named (e.g. the follow-up list when you say 'due for a follow-up'). Keep the DEMO DATA label visible. Do not speed up the playback clip.

**TRANSITION TO NEXT SCENE:** Quick dissolve from the insights table to a close-up of your hands on the tablet.

### Scene 5 - Real execution

**SCENE:** Scene 5 - Real execution  (file `VO_005_EXECUTION.wav`)

**PURPOSE:** Contrast planning with doing. Show an actual working session, including the uncomfortable moment.

**ESTIMATED DURATION:** plan 5:30-7:30 · estimated from the text: 1:57 (255 own words + 2 placeholder(s)). The real length is whatever you record; the edit adapts to it.

**VOICEOVER:**

> Planning is comfortable. Execution is where it gets real.
>
> Here's how a working session goes now.
>
> I open the Today screen. It shows what's due. I pick a business and start with research. Ten minutes, no more. I write down one specific thing I noticed about them, something true and relevant. That's what keeps the message from sounding like everyone else's.
>
> Then I decide whether they're worth contacting. Qualified, maybe, or no. Writing no down is a win. It saves me time.
>
> I'm trying to be strict about this. A business I like the idea of isn't the same as a business that actually has the problem I solve.
>
> If it's a yes, I follow the first-message playbook. One channel. One short message. One small question. I give the approach a name, so I can compare it with the others later.
>
> Then comes the part that's genuinely uncomfortable: pressing send. [RECORD: in one or two sentences, what that moment feels like for you. Only say this if you've actually done it.]
>
> After I send it, I log it, and I set a follow-up date before I close the form. That small habit is the whole system. A message with no follow-up date is a message I'll forget.
>
> [FILL: one real example with the name removed. What you sent, and what happened. If nothing happened yet, say what you did next.]
>
> And when someone replies, I record it, and the tool moves them forward. A meeting. A proposal. A yes or a no. Each step gets a date.
>
> The numbers that matter right now aren't revenue. They're simpler. How many real messages went out. How many follow-ups I actually did. How many people replied.
>
> None of this is clever. That's the point. It's a way to turn effort into evidence.

**VISUALS:** Real footage wherever possible: your Today screen on a real morning, the real research notes (blurred), the playbook ticking, the log form after a real send, the follow-up appearing on Today.

**SCREEN RECORDING:** B03, B02, B04 (yours). A03, A04 (captured by me, DEMO DATA). C01 only if a real reply has arrived (optional).

**EDITING NOTES:** Cut to real footage on 'pressing send' and hold. Keep the screen readable for at least 3 seconds per step. Use full-screen text only for 'A follow-up date.'

**TRANSITION TO NEXT SCENE:** Fade the tablet footage down; hold a plain frame for half a second before the product-opportunity scene.

### Scene 6 - The product opportunity

**SCENE:** Scene 6 - The product opportunity  (file `VO_006_OPPORTUNITY.wav`)

**PURPOSE:** Explain the second business honestly, with no product-market-fit claim.

**ESTIMATED DURATION:** plan 7:30-9:00 · estimated from the text: 1:37 (231 own words + 0 placeholder(s)). The real length is whatever you record; the edit adapts to it.

**VOICEOVER:**

> Here's the bigger question. Could this software be a product?
>
> I think there's a version of it that could help other people. Freelancers. Small agencies. Anyone building a business through outreach who needs a way to know what to do today, and what worked last week.
>
> But I want to be careful. Right now I have exactly one user: me. Zero customers for the software. I'm not claiming anybody wants it. I haven't proven anything.
>
> What I do have is an advantage. I'm building it from a problem I'm living in real time. Every feature exists because I either needed it, or found out I didn't.
>
> A tool like this would have to be simple enough that one person can use it in ten minutes a day, and solid enough that a small team could share it later. That's the target. I'm a long way from knowing if I've hit it.
>
> So here's the rule. The software has to earn its place in my own week first. If I keep using it when I'm busy, and it keeps showing me things I would have missed, that's a signal. If I stop opening it, that's a signal too, and I'll tell you.
>
> Only then does it make sense to ask whether someone else would pay for it.
>
> Two businesses, one experiment. But the second one only exists if the first one works.

**VISUALS:** Calm product footage (playbook editor, duplicate a playbook for a different offer), then a plain text card of the rule.

**SCREEN RECORDING:** A08, A06 (captured, demo). B07 (yours).

**EDITING NOTES:** Full-screen text: 'The software has to earn its place in my own week first.' Keep it on screen for the whole sentence.

**TRANSITION TO NEXT SCENE:** Slow push into the final scene's desk shot.

### Scene 7 - The journey ahead

**SCENE:** Scene 7 - The journey ahead  (file `VO_007_CLOSING.wav`)

**PURPOSE:** State the challenge and the unknowns, explain why you're documenting, and invite people to follow.

**ESTIMATED DURATION:** plan 9:00-11:30 · estimated from the text: 1:39 (213 own words + 2 placeholder(s)). The real length is whatever you record; the edit adapts to it.

**VOICEOVER:**

> So what happens next?
>
> Here's the challenge. [FILL: your real goal for the next stretch, in your own words. The project notes mention a stretch target of ten thousand dollars in November, described there as a target, not a forecast. Say it only if it is still true, and say it that way.]
>
> Here's what I don't know yet. Whether my offer is the right one. Whether my price is right. Whether the people I'm contacting will answer at all. And whether this software is something I'll still be using in a month.
>
> I'd rather say that out loud than pretend I've got it figured out.
>
> Why film it? Because there's a version of starting that nobody shows you. Not the polished launch. The Tuesday where you send a message and hear nothing. The small change that finally works. The numbers going up slowly, or not at all.
>
> If you're thinking about starting something, I want you to see that you can start with what you have. I'm not starting with a big budget. I'm starting with a plan, a tool I'm building, and a list of real people.
>
> In the next episode, [FILL: what you'll show next. Suggested: the first real results from the outreach, whatever they turn out to be.]
>
> You can expect a long episode like this regularly, with shorter clips in between, built from whatever I actually did that day. If a week is quiet, I'll tell you it was quiet.
>
> If you want to watch whether this works, or watch it fall apart, subscribe and follow along. I'll show you every step.
>
> I'm Andrew. This is the Bootstrapper Experiment. Let's see what happens.

**VISUALS:** You at your desk, or the tablet showing the Today screen at the start of a new day. End on the title card and the subscribe prompt.

**SCREEN RECORDING:** B03, B06 (yours). A05 (captured, demo) as a quiet backdrop for the closing lines.

**EDITING NOTES:** Music swells slightly on the invitation, then drops out for the last line so the voice finishes alone. End card for 6 seconds.

**TRANSITION TO NEXT SCENE:** End card.

