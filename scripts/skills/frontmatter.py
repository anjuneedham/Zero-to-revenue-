"""Tiny SKILL.md frontmatter reader (stdlib only; uses PyYAML if it happens to be installed)."""
import re

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.S)


def read(path):
    """Return (frontmatter_dict, error_or_None)."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        return {}, f"unreadable: {e}"
    m = _FM.match(text)
    if not m:
        return {}, "no YAML frontmatter block"
    block = m.group(1)
    try:
        import yaml  # optional

        data = yaml.safe_load(block)
        if not isinstance(data, dict):
            return {}, "frontmatter is not a mapping"
        return data, None
    except ImportError:
        pass
    except Exception as e:  # malformed YAML
        return {}, f"invalid YAML: {e}"
    # Fallback: top-level scalars and folded/literal blocks only.
    data, key, buf, style = {}, None, [], None
    for line in block.split("\n"):
        top = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if top:
            if key is not None:
                data[key] = _join(buf, style)
            key, rest = top.group(1), top.group(2).strip()
            if rest in (">", ">-", "|", "|-", ">+", "|+"):
                style, buf = rest[0], []
            else:
                style, buf = None, [rest.strip("\"'")]
        elif key is not None:
            buf.append(line.strip())
    if key is not None:
        data[key] = _join(buf, style)
    return data, None


def _join(buf, style):
    return ("\n" if style == "|" else " ").join(b for b in buf if b != "").strip()
