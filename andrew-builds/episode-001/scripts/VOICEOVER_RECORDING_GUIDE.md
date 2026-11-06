# Voiceover Recording Guide (Episode 001)

You record the narration. This file is the session plan. One file per section, so any section can be re-recorded and swapped without rebuilding the episode.

## Before you start
1. Record in a quiet room. Switch off fans, air conditioning, notifications and phones. Soft furnishings help; a wardrobe of clothes works well.
2. Use the same microphone at the same distance (a hand's width from your mouth, slightly off-axis) for every section and every session.
3. Record a 10-second test first. Play it back with headphones. Fix hiss, echo or popping before you continue.
4. Keep peaks around -12 dB. If the meter touches red, move back or lower the gain. **Clipped audio cannot be repaired.**
5. Record each section more than once if you stumble. Keep every take.
6. Leave about one second of silence before and after each section. The edit trims it.
7. Keep the original recordings untouched. Do not add EQ, compression, noise reduction or effects. The pipeline normalises loudness only.
8. Save as **WAV**, any sample rate 44.1 or 48 kHz, mono or stereo, with the exact file names below, into `episode-001/voiceover/`.

## Fill the placeholders first
Open `EPISODE_001_MASTER_SCRIPT.md` and decide what you will really say at each `[FILL]` / `[RECORD]`. Then put the same words into
`editing-project/episode_001.json` (replace the bracket) so the captions match what you recorded. If you would rather speak freely, record first and
replace the captions with a transcript of your recording (see EPISODE_001_EDITING_PLAN.md, "Captions").

## Replacing one section later
Record a new `VO_00X_NAME.wav` with the same name, then run `python3 andrew-builds/tools/produce.py episode`. Only the changed scene is re-rendered (scenes are cached by content).

## Robot guide tracks
`voiceover/_scratch/` holds robot (text-to-speech) tracks made only to test timing and captions. They are **not** narration and are never used unless you pass `--scratch-vo`. Your real files always take priority.

## 1. `VO_001_HOOK.wav`  (Scene 1 - Cold open)

- **Approx. duration:** 0:55 (robot guide track measured 0:46)
- **Tone:** Direct, quiet confidence. A little curious. Not hyped.
- **Pace:** Medium-fast on the questions, slower on 'Episode one.'
- **Emphasis:** 'just started', 'second experiment', 'two businesses'
- **Pauses:** 1 beat after 'What if I just started?'; 1 beat after 'second experiment hiding inside the first.'

**Script:**

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

## 2. `VO_002_BACKGROUND.wav`  (Scene 2 - The background)

- **Approx. duration:** 1:32 (robot guide track measured 1:12)
- **Tone:** Conversational, like telling a friend. Plain and a little self-aware.
- **Pace:** Relaxed. Slow down on the zero.
- **Emphasis:** 'Zero.' 'it isn't.' 'Including the bad ones.'
- **Pauses:** 2 beats after 'Zero.'; 1 beat after 'it isn't.'

**Script:**

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

## 3. `VO_003_BUSINESS.wav`  (Scene 3 - The business)

- **Approx. duration:** 1:23 (robot guide track measured 0:58)
- **Tone:** Matter-of-fact. Specific. No selling.
- **Pace:** Steady. Slow down on the status line.
- **Emphasis:** 'Ten or fifteen honest ones.' the real status line
- **Pauses:** 1 beat before the status line.

**Script:**

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

## 4. `VO_004_SOFTWARE.wav`  (Scene 4 - The software)

- **Approx. duration:** 2:20 (robot guide track measured 2:06)
- **Tone:** Enthusiastic but grounded. Like showing a friend something you built.
- **Pace:** Medium. Pause so the screen can be read.
- **Emphasis:** 'remembering', 'one of six', 'it doesn't pretend to be smart'
- **Pauses:** 1 beat after each playbook example; 2 beats after 'Nothing gets quietly rewritten.'

**Script:**

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

## 5. `VO_005_EXECUTION.wav`  (Scene 5 - Real execution)

- **Approx. duration:** 1:57 (robot guide track measured 1:40)
- **Tone:** Honest, a bit vulnerable on the 'press send' line. Practical elsewhere.
- **Pace:** Slower and warmer on the press-send moment.
- **Emphasis:** 'pressing send', 'a follow-up date', 'turn effort into evidence'
- **Pauses:** 2 beats before 'pressing send.'

**Script:**

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

## 6. `VO_006_OPPORTUNITY.wav`  (Scene 6 - The product opportunity)

- **Approx. duration:** 1:37 (robot guide track measured 1:20)
- **Tone:** Thoughtful. Careful with claims.
- **Pace:** Measured. Slow down on 'exactly one user.'
- **Emphasis:** 'exactly one user: me', 'earn its place'
- **Pauses:** 2 beats after 'I haven't proven anything.'

**Script:**

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

## 7. `VO_007_CLOSING.wav`  (Scene 7 - The journey ahead)

- **Approx. duration:** 1:39 (robot guide track measured 1:18)
- **Tone:** Warm, honest, forward-looking. Not salesy.
- **Pace:** Unhurried. Slow on the last two lines.
- **Emphasis:** 'I'd rather say that out loud', 'start with what you have'
- **Pauses:** 2 beats after 'pretend I've got it figured out.'; 1 beat before 'Let's see what happens.'

**Script:**

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


## Short-form narration files
- `VO_S1_START.wav`: Start Before You're Ready (see `SHORTS_001_SCRIPTS.md`)
- `VO_S2_TOOL.wav`: Building the Tool I Need (see `SHORTS_001_SCRIPTS.md`)
- `VO_S3_TWO.wav`: Two Businesses, One Experiment (see `SHORTS_001_SCRIPTS.md`)
