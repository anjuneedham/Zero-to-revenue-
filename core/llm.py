"""Thin Claude client shared by the AI command center and lead ingestion. The caller owns budget, validation and what the
output may do; this wrapper only makes the call."""

import os


class ClaudeClient:
    """Thin wrapper over the Anthropic SDK (lazy import). Not exercised against the live API in tests."""

    def __init__(self, model: str | None = None):
        import anthropic
        self.model = model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
        self.client = anthropic.Anthropic()  # ANTHROPIC_API_KEY from the environment

    def complete(self, system: str, user: str, max_tokens: int, image=None):
        content = user if image is None else [
            {"type": "image", "source": {"type": "base64", "media_type": image[0], "data": image[1]}},
            {"type": "text", "text": user}]
        r = self.client.messages.create(model=self.model, max_tokens=max_tokens, system=system,
                                        messages=[{"role": "user", "content": content}])
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return text, r.usage.input_tokens, r.usage.output_tokens
