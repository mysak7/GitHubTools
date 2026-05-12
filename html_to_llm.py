#!/usr/bin/env python3
"""Strip HTML down to token-efficient plain text for LLM input."""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path


# Void elements have no closing tag — skip them when depth-counting
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "li", "tr", "br",
    "blockquote", "pre", "code", "td", "th", "ul", "ol", "table",
}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def strip_skip_blocks(html: str) -> str:
    """Remove style/script/head blocks via regex before parsing."""
    for tag in ("head", "style", "script", "svg", "noscript", "iframe", "canvas"):
        html = re.sub(
            rf"<{tag}[\s>].*?</{tag}>",
            " ", html,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return html


class LLMExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in HEADING_TAGS:
            level = int(tag[1])
            self.parts.append("\n" + "#" * level + " ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in BLOCK_TAGS | HEADING_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text + " ")

    def get_text(self):
        raw = "".join(self.parts)
        raw = re.sub(r" {2,}", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_llm(html: str) -> str:
    html = strip_skip_blocks(html)
    parser = LLMExtractor()
    parser.feed(html)
    return parser.get_text()


def main():
    if len(sys.argv) < 2:
        print("Usage: html_to_llm.py <file.html> [output.txt]", file=sys.stderr)
        sys.exit(1)

    src = Path(sys.argv[1])
    with src.open(encoding="utf-8") as f:
        html = f.read()

    original_bytes = len(html.encode())
    result = html_to_llm(html)
    result_bytes = len(result.encode())
    savings = 100 * (1 - result_bytes / original_bytes)

    out = Path(sys.argv[2]) if len(sys.argv) >= 3 else src.with_name(src.stem + "_llm.txt")
    out.write_text(result, encoding="utf-8")
    print(f"Saved to {out}")

    print(f"[{original_bytes:,}B → {result_bytes:,}B, -{savings:.0f}% tokens]",
          file=sys.stderr)


if __name__ == "__main__":
    main()
