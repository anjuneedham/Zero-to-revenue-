---
name: copyable-blocks
description: Present anything the user has to copy and paste elsewhere (WhatsApp/DM messages, prompts, links, commands, emails, captions) as a clean fenced code block so it can be copied in one tap. Use whenever a reply contains text meant to be sent, pasted or run.
---

# Copyable blocks

Anything the user must copy goes in its own fenced code block. Never inline it in prose, bold it or put it in a blockquote, because those formats carry stray characters and break on copy.

## Rules

1. **One item per block.** One message, one prompt, one link, one command. Several messages means several blocks, each labelled in plain text above it ("Message 1 of 2").
2. **Only the text to send goes in the block.** No labels, quotes, "Send this:", explanations or placeholders left unfilled. The user must be able to copy the block and send it as-is.
3. **Use a plain fence with no language tag** for messages and prompts (```` ``` ````). Use a language tag only for real code or shell commands.
4. **Keep line breaks and emoji exactly as they should be sent.** Do not wrap lines by hand.
5. **Links go in their own block**, one per block, with no trailing punctuation.
6. **Explanation goes outside the block**: a short label before it, and the reasoning or next steps after it. Keep that brief.
7. **If something needs filling in** (a name, number, price), ask for it or choose a sensible default before the block. Do not put `[brackets]` inside a block the user will send, unless they asked for a template.
8. **Never invent facts** inside a copyable message: no features, prices, results or promises the product docs don't support. Check the repo docs first when unsure.

## Format

Label in plain text, then the block, then at most a few lines of why or what next:

    Message to send:

    ```
    <the exact text>
    ```

    Why it works / what to check next: ...
