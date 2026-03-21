#!/usr/bin/env python3
"""
ESV Reader's Bible PDF Parser
==============================
Extracts verse-by-verse text from the ESV Reader's Bible with Chapter and
Verse Numbers PDF into CSV or JSON.

Usage:
    python esv_parser.py <input.pdf> [output.csv|output.json] [-v]

Requirements:
    pip install pdfplumber

Layout assumptions (from ESV Reader's Bible with Chapter & Verse Numbers):
    - Two-column layout, ~792pt wide
    - Chapter numbers:   standalone digits at body-text size (~11.8pt)
    - Verse numbers:     superscript digits (~5.5pt height)
    - Drop caps:         large decorative letters (>20pt) at section starts
    - Page headers:      italic book/chapter refs at top (<80pt y)
    - Section headers:   UPPERCASE text at ~9.5pt ("CREATION AND THE FALL")
    - Body text:         ~11.8pt TriniteNo2-Roman
"""

import pdfplumber
import re
import csv
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


# --- Bible book reference ---------------------------------------------------

BIBLE_BOOKS = [
    ("Genesis", 50), ("Exodus", 40), ("Leviticus", 27), ("Numbers", 36),
    ("Deuteronomy", 34), ("Joshua", 24), ("Judges", 21), ("Ruth", 4),
    ("1 Samuel", 31), ("2 Samuel", 24), ("1 Kings", 22), ("2 Kings", 25),
    ("1 Chronicles", 29), ("2 Chronicles", 36), ("Ezra", 10), ("Nehemiah", 13),
    ("Esther", 10), ("Job", 42), ("Psalms", 150), ("Proverbs", 31),
    ("Ecclesiastes", 12), ("Song of Solomon", 8), ("Isaiah", 66),
    ("Jeremiah", 52), ("Lamentations", 5), ("Ezekiel", 48), ("Daniel", 12),
    ("Hosea", 14), ("Joel", 3), ("Amos", 9), ("Obadiah", 1), ("Jonah", 4),
    ("Micah", 7), ("Nahum", 3), ("Habakkuk", 3), ("Zephaniah", 3),
    ("Haggai", 2), ("Zechariah", 14), ("Malachi", 4),
    ("Matthew", 28), ("Mark", 16), ("Luke", 24), ("John", 21),
    ("Acts", 28), ("Romans", 16), ("1 Corinthians", 16), ("2 Corinthians", 13),
    ("Galatians", 6), ("Ephesians", 6), ("Philippians", 4), ("Colossians", 4),
    ("1 Thessalonians", 5), ("2 Thessalonians", 3), ("1 Timothy", 6),
    ("2 Timothy", 4), ("Titus", 3), ("Philemon", 1), ("Hebrews", 13),
    ("James", 5), ("1 Peter", 5), ("2 Peter", 3), ("1 John", 5),
    ("2 John", 1), ("3 John", 1), ("Jude", 1), ("Revelation", 22),
]

BOOK_NAMES = [b[0] for b in BIBLE_BOOKS]
BOOK_CHAPTERS = {b[0]: b[1] for b in BIBLE_BOOKS}

# Map UPPERCASE title -> canonical name (for title-page detection)
BOOK_ALIASES = {}
for _name in BOOK_NAMES:
    BOOK_ALIASES[_name.upper()] = _name
    BOOK_ALIASES[_name.upper().replace(" ", "")] = _name


# --- Size thresholds --------------------------------------------------------
# Word "size" = bottom - top (bounding-box height in pts).

SIZE_SUPERSCRIPT = 6.0       # verse-number superscripts are ~5.5
SIZE_SECTION_HEADER = 10.0   # section headers are ~9.5
SIZE_PAGE_HEADER = 10.5      # running headers & page numbers are ~10.0
SIZE_BODY_TEXT = 11.0         # body text and chapter markers are ~11.8
SIZE_DROP_CAP = 20.0          # decorative drop caps are ~34

# Single letters that are standalone words, not drop-cap prefixes
STANDALONE_LETTERS = {"I", "A", "O"}


# --- Data structures --------------------------------------------------------

@dataclass
class Verse:
    book: str
    chapter: int
    verse: int
    text: str


# --- Layout detection -------------------------------------------------------

def detect_layout(pdf):
    """Detect page dimensions and layout constants."""
    page = pdf.pages[min(3, len(pdf.pages) - 1)]
    return {
        "page_width": page.width,
        "col_midpoint": page.width / 2,
        "col_gap": 30,
        "header_y_max": 80,
        "footer_y_min": 500,
    }


# --- Word classification ----------------------------------------------------

def classify_word(w, layout, expected_chapter, current_book=None):
    text = w["text"]
    y = w["top"]
    size = round(w["bottom"] - w["top"], 1)

    # 1. Page numbers / Headers / Sections (SKIP)
    if y < layout["header_y_max"] or y > layout["footer_y_min"]:
        if size < SIZE_PAGE_HEADER:
            return ("SKIP", text)

    # Section headers: small uppercase text, but detect "PSALM" headers specially
    if size <= SIZE_SECTION_HEADER and text.isupper() and len(text) >= 2:
        if text == "PSALM" and current_book == "Psalms":
            return ("PSALM_HEADER", text)
        return ("SKIP", text)

    # 2. Drop caps
    if size > SIZE_DROP_CAP and len(text) == 1:
        return ("DROP_CAP", text)

    # 3. Superscript verse numbers
    if size < SIZE_SUPERSCRIPT and re.match(r"^\d{1,3}$", text):
        return ("VERSE", text)

    # 4. Chapter markers — require position near a column's left edge
    if (size >= SIZE_BODY_TEXT
            and re.match(r"^\d{1,3}$", text)
            and int(text) == expected_chapter):
        max_chapters = BOOK_CHAPTERS.get(current_book, 999)
        if int(text) <= max_chapters:
            x = w["x0"]
            mid = layout["col_midpoint"]
            left_col_start = 70
            right_col_start = mid + 20
            near_col_start = (x < left_col_start + 50 or
                              abs(x - right_col_start) < 50)
            if near_col_start:
                return ("CHAPTER", text)

    # 5. VERSE PREFIX (The critical fix)
    # Broaden to catch digits followed by: letters, quotes, or parentheses.
    # Pattern: Digit(s) + (Anything that isn't just a digit)
    m = re.match(r"^(\d{1,3})([A-Za-z\(\"\u2018\u201c\u2019\u201d].*)", text)
    if m and size >= SIZE_BODY_TEXT:
        vn = int(m.group(1))
        # Logic guard: prevents catching years like "110 years" in genealogies
        if 1 <= vn <= 176:
            return ("VERSE_PREFIX", text)

    return ("TEXT", text)



# --- Column-aware word ordering ---------------------------------------------

def get_sorted_words(page, layout):
    raw = page.extract_words()
    if not raw: return []

    mid = layout["col_midpoint"]
    expanded = []

    # Regex to split text ending in punctuation from an immediate verse number
    # Handles: "ground—7then", "Bethuel.”23(Bethuel", "field.32The"
    split_pattern = re.compile(r'^(.*?[\u2014\-\.!?"\u201d\u2019\)])\s*(\d{1,3})([\(A-Za-z\u201c\u2018"].*)$')

    for w in raw:
        m = split_pattern.match(w["text"])
        if m:
            # Part 1: Tail end of the previous verse
            w1 = w.copy()
            w1["text"] = m.group(1).strip()
            expanded.append(w1)
            
            # Part 2: Start of the new verse
            w2 = w.copy()
            w2["text"] = m.group(2) + m.group(3)
            w2["x0"] = w["x0"] + (len(m.group(1)) * 3) # Offset x for logic
            expanded.append(w2)
        else:
            expanded.append(w)

    # Bucketing columns strictly prevents 'backwards' errors
    left = [w for w in expanded if w["x1"] < mid]
    right = [w for w in expanded if w["x0"] >= mid]

    def sort_col(words):
        # 5pt Y-tolerance snaps superscripts to their baseline
        return sorted(words, key=lambda w: (round(w["top"] / 5) * 5, w["x0"]))

    return sort_col(left) + sort_col(right)

# --- Book title page detection ----------------------------------------------

def detect_book_title(page):
    """
    Check if a page is a book title page.
    Handles long titles like 'The Gospel According to John' or 'The Psalms'.
    """
    raw_text = page.extract_text() or ""
    # Title pages have very little text (usually < 150 chars including whitespace)
    if len(raw_text.strip()) > 150:
        return None

    # 1. Normalize: Uppercase and collapse multiple spaces/newlines
    clean_text = " ".join(raw_text.upper().split())
    
    # 2. Collapse ALL spaces for the 'hard' match (handles "G E N E S I S")
    shorthand = clean_text.replace(" ", "")

    # 3. Check for exact alias matches first
    if clean_text in BOOK_ALIASES:
        return BOOK_ALIASES[clean_text]
    if shorthand in BOOK_ALIASES:
        return BOOK_ALIASES[shorthand]

    # 4. Fuzzy match: Check if the canonical book name is part of the title
    # Sort by length descending so "1 Samuel" is checked before "Samuel"
    sorted_names = sorted(BOOK_NAMES, key=len, reverse=True)
    for name in sorted_names:
        name_upper = name.upper()
        # Does 'JOHN' appear in 'THE GOSPEL ACCORDING TO JOHN'?
        if name_upper in clean_text:
            # Additional check: ensure it's not just a partial word 
            # (e.g., 'Amos' inside 'Amos')
            if re.search(rf'\b{re.escape(name_upper)}\b', clean_text):
                return name

    return None


# --- Text cleanup -----------------------------------------------------------

def clean_verse_text(text):
    if not text: return ""
    # Standard normalization
    text = text.replace("\u00a0", " ")
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # Fix Drop Cap spacing (e.g., "T he" -> "The") but not standalone words (I, A, O)
    text = re.sub(r"^([B-HJ-NP-Z])\s+([a-z])", r"\1\2", text)
    # Join hyphenated line breaks
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# --- Main parser ------------------------------------------------------------

def parse_bible_pdf(pdf_path, current_book, verbose=False):
    """
    Parse an ESV Reader's Bible PDF into a list of Verse objects.

    Strategy:
      1. Detect book title pages to track current book.
      2. Classify each word by its bounding-box height into:
         CHAPTER, VERSE, DROP_CAP, VERSE_PREFIX, TEXT, or SKIP.
      3. Use `expected_chapter` to disambiguate chapter markers from
         in-text numbers (e.g. ages in genealogies).
      4. Merge drop caps with their continuation word directly in the
         parser (avoiding false-positive regex joins like "I will" -> "Iwill").
    """
    pdf = pdfplumber.open(pdf_path)
    try:
        layout = detect_layout(pdf)

        verses = []
        current_chapter = 0
        expected_chapter = 1
        current_verse = 0
        text_buf = []

        def flush():
            nonlocal text_buf
            if current_book and current_chapter > 0 and current_verse > 0 and text_buf:
                raw = " ".join(text_buf)
                cleaned = clean_verse_text(raw)
                if cleaned:
                    verses.append(Verse(current_book, current_chapter,
                                        current_verse, cleaned))
            text_buf = []

        total = len(pdf.pages)

        for page_idx in range(total):
            page = pdf.pages[page_idx]

            if verbose and page_idx % 100 == 0:
                print(f"  Page {page_idx + 1}/{total}...", file=sys.stderr)

            # Skip title pages (first page or pages with very little text)
            title = detect_book_title(page)
            if title:
                if verbose:
                    print(f"  Title page: {title}", file=sys.stderr)
                continue

            words = get_sorted_words(page, layout)
            if not words:
                continue

            i = 0
            while i < len(words):
                tag, raw_text = classify_word(
                    words[i], layout, expected_chapter, current_book)

                if tag == "SKIP":
                    i += 1
                    continue

                # -- PSALM header: "PSALM" followed by a number --
                if tag == "PSALM_HEADER":
                    # Look ahead for the psalm/chapter number
                    if i + 1 < len(words):
                        nxt = words[i + 1]
                        nxt_text = nxt["text"]
                        if re.match(r"^\d{1,3}$", nxt_text):
                            flush()
                            current_chapter = int(nxt_text)
                            expected_chapter = current_chapter + 1
                            current_verse = 0  # wait for verse superscript
                            text_buf = []
                            if verbose and current_chapter % 10 == 1:
                                print(f"  Psalm {current_chapter}",
                                      file=sys.stderr)
                            i += 2
                            continue
                    i += 1
                    continue

                # -- Auto-set chapter 1 for single-chapter books --
                if (current_chapter == 0
                        and tag in ("VERSE", "VERSE_PREFIX", "TEXT",
                                    "DROP_CAP")
                        and BOOK_CHAPTERS.get(current_book, 0) == 1):
                    current_chapter = 1
                    expected_chapter = 2

                # -- Auto-set verse 1 when chapter exists but no verse yet --
                # Only for body-text-sized content (skip psalm superscriptions
                # which are ~10.6pt, below SIZE_BODY_TEXT)
                if (current_chapter > 0 and current_verse == 0
                        and tag in ("TEXT", "DROP_CAP")):
                    word_size = round(words[i]["bottom"] - words[i]["top"], 1)
                    if word_size >= SIZE_BODY_TEXT or tag == "DROP_CAP":
                        current_verse = 1
                    else:
                        # Skip sub-body-text content (e.g. psalm superscriptions)
                        i += 1
                        continue

                # -- CHAPTER marker --
                if tag == "CHAPTER":
                    # Look back: if the previous word was a drop cap that we
                    # already appended to text_buf, pull it out so we can
                    # re-attach it to the new chapter's verse 1.
                    drop_cap = ""
                    if i > 0:
                        prev = words[i - 1]
                        prev_size = round(prev["bottom"] - prev["top"], 1)
                        if (prev_size > SIZE_DROP_CAP
                                and len(prev["text"]) == 1
                                and prev["text"].isalpha()):
                            drop_cap = prev["text"]
                            if text_buf and text_buf[-1] == prev["text"]:
                                text_buf.pop()
    
                    flush()
                    current_chapter = int(raw_text)
                    expected_chapter = current_chapter + 1
                    current_verse = 1
                    text_buf = []
    
                    # Merge drop cap with the next word (the continuation fragment).
                    # E.g. drop_cap="I" + next word "n" -> "In"
                    #      drop_cap="T" + next word "his" -> "This"
                    #      drop_cap="N" + next word "ow" -> "Now"
                    if drop_cap:
                        if i + 1 < len(words):
                            nxt_tag, nxt_text = classify_word(
                                words[i + 1], layout, expected_chapter,
                                current_book)
                            if (nxt_tag == "TEXT"
                                    and nxt_text
                                    and nxt_text[0].islower()):
                                sep = " " if drop_cap in STANDALONE_LETTERS else ""
                                text_buf.append(drop_cap + sep + nxt_text)
                                i += 2  # skip chapter marker + fragment
                                continue
                        # Fallback: add drop cap as standalone word
                        text_buf.append(drop_cap)

                    i += 1
                    continue

                # -- DROP_CAP without preceding chapter marker --
                if tag == "DROP_CAP":
                    letter = raw_text
                    if i + 1 < len(words):
                        nxt_tag, nxt_text = classify_word(
                            words[i + 1], layout, expected_chapter,
                            current_book)
                        if (nxt_tag == "TEXT"
                                and nxt_text
                                and nxt_text[0].islower()):
                            sep = " " if letter in STANDALONE_LETTERS else ""
                            text_buf.append(letter + sep + nxt_text)
                            i += 2
                            continue
                    text_buf.append(letter)
                    i += 1
                    continue
    
                # -- Superscript VERSE number --
                if tag == "VERSE":
                    new_v = int(raw_text)
                    # Skip redundant verse 1 if already at verse 1 with no text
                    if not (new_v == current_verse and not text_buf):
                        flush()
                    current_verse = new_v
                    text_buf = []
                    i += 1
                    continue
    
                # -- VERSE_PREFIX: digits fused with text, e.g. "25And" --
                if tag == "VERSE_PREFIX":
                    m = re.match(r"^(\d{1,3})(.*)", raw_text)
                    if m:
                        flush()
                        current_verse = int(m.group(1))
                        text_buf = []
                        remainder = m.group(2)
                        if remainder:
                            text_buf.append(remainder)
                    i += 1
                    continue
    
                # -- Regular TEXT --
                if tag == "TEXT":
                    text_buf.append(raw_text)
                    i += 1
                    continue
    
                i += 1
    
        flush()
        return verses
    finally:
        pdf.close()


# --- Validation -------------------------------------------------------------

def validate(verses, verbose=False):
    """Check verse continuity and report issues."""
    issues = []
    prev_book = prev_ch = prev_v = None

    for v in verses:
        if v.book == prev_book and v.chapter == prev_ch and prev_v is not None:
            if v.verse != prev_v + 1:
                direction = "backwards" if v.verse <= prev_v else "skipped"
                issues.append(
                    f"  {direction}: {v.book} {v.chapter}:{prev_v} -> {v.verse}")
        if not v.text.strip():
            issues.append(f"  empty: {v.book} {v.chapter}:{v.verse}")
        prev_book, prev_ch, prev_v = v.book, v.chapter, v.verse

    if verbose:
        books = {}
        for v in verses:
            if v.book not in books:
                books[v.book] = {"chapters": set(), "count": 0}
            books[v.book]["chapters"].add(v.chapter)
            books[v.book]["count"] += 1

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  Total: {len(verses)} verses, {len(books)} book(s)",
              file=sys.stderr)
        for bk, info in books.items():
            exp = BOOK_CHAPTERS.get(bk, "?")
            print(f"  {bk}: {info['count']} verses, "
                  f"{len(info['chapters'])} chapters (of {exp})",
                  file=sys.stderr)

        if issues:
            print(f"\n  {len(issues)} issue(s):", file=sys.stderr)
            for iss in issues[:30]:
                print(iss, file=sys.stderr)
        else:
            print(f"\n  No issues.", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

    return issues


# --- Output writers ---------------------------------------------------------

def write_csv(verses, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["book", "chapter", "verse", "text"])
        for v in verses:
            w.writerow([v.book, v.chapter, v.verse, v.text])


def write_json(verses, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(v) for v in verses], f, indent=2, ensure_ascii=False)


# --- CLI --------------------------------------------------------------------

def main():
    output_path = Path(__file__).resolve().parent.parent / "data" / "bible.csv"
    esv_dir = Path(__file__).resolve().parent.parent / "data" / "esv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["book", "chapter", "verse", "text"])

        for pdf_path in sorted(esv_dir.rglob("*.pdf")):
            print(f"Parsing: {pdf_path.stem.split('.')[-1]}", file=sys.stderr)
            verses = parse_bible_pdf(pdf_path, pdf_path.stem.split('.')[-1], verbose=True)

            if not verses:
                print("ERROR: No verses found. Is this an ESV Reader's Bible PDF?", file=sys.stderr)
                #sys.exit(1)

            validate(verses, verbose=True)

            # Preview
            print(f"First 10 verses:")
            for v in verses[:10]:
                preview = v.text[:100] + "..." if len(v.text) > 100 else v.text
                print(f"  {v.book} {v.chapter}:{v.verse}  {preview}")
            print(f"\nLast 5 verses:")
            for v in verses[-5:]:
                preview = v.text[:100] + "..." if len(v.text) > 100 else v.text
                print(f"  {v.book} {v.chapter}:{v.verse}  {preview}")

            for v in verses:
                w.writerow([v.book, v.chapter, v.verse, v.text])

            print(f"\nSaved {len(verses)} verses -> {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()