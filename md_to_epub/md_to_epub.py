#!/usr/bin/env python3
"""Convert Markdown file(s) to EPUB."""

import argparse
import re
import sys
from pathlib import Path

# --- config ---
DEFAULT_AUTHOR = "Michal"
DEFAULT_LANGUAGE = "cs"
DEFAULT_INPUT_DIR = Path(__file__).parent
# --------------

try:
    import markdown
    from ebooklib import epub
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install ebooklib markdown")
    sys.exit(1)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def md_to_epub(
    input_paths: list[Path],
    output_path: Path,
    title: str | None = None,
    author: str = "Unknown",
    language: str = "en",
) -> None:
    book = epub.EpubBook()
    book.set_language(language)
    book.add_author(author)

    chapters: list[epub.EpubHtml] = []
    spine = ["nav"]

    for i, path in enumerate(input_paths):
        md_text = path.read_text(encoding="utf-8")
        chapter_title = path.stem

        if i == 0 and title is None:
            title = chapter_title

        html_content = markdown.markdown(
            md_text,
            extensions=["fenced_code", "tables", "toc", "nl2br"],
        )

        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f"{slugify(chapter_title)}-{i}.xhtml",
            lang=language,
        )
        chapter.content = f"<h1>{chapter_title}</h1>\n{html_content}"
        book.add_item(chapter)
        chapters.append(chapter)
        spine.append(chapter)

    book.set_title(title or "Untitled")
    book.toc = tuple(epub.Link(c.file_name, c.title, c.file_name) for c in chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    epub.write_epub(str(output_path), book)
    print(f"Written: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Markdown to EPUB")
    parser.add_argument("inputs", nargs="*", type=Path, help="Markdown file(s) or dirs (default: script's own dir)")
    parser.add_argument("-o", "--output", type=Path, help="Output .epub path (default: <first_file>.epub)")
    parser.add_argument("-t", "--title", help="Book title (default: first filename)")
    parser.add_argument("-a", "--author", default=DEFAULT_AUTHOR, help=f"Author name (default: {DEFAULT_AUTHOR})")
    parser.add_argument("-l", "--language", default=DEFAULT_LANGUAGE, help=f"Language code (default: {DEFAULT_LANGUAGE})")
    args = parser.parse_args()

    raw = args.inputs or [DEFAULT_INPUT_DIR]
    inputs: list[Path] = []
    for p in raw:
        if p.is_dir():
            inputs.extend(sorted(f for f in p.glob("*.md") if f.name != p.name))
        else:
            inputs.append(p)

    if not inputs:
        print(f"No Markdown files found in {raw}.")
        sys.exit(1)

    output = args.output or (DEFAULT_INPUT_DIR / f"{inputs[0].stem}.epub")

    md_to_epub(inputs, output, title=args.title, author=args.author, language=args.language)


if __name__ == "__main__":
    main()
