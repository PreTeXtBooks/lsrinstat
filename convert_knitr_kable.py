#!/usr/bin/env python3
"""Convert knitr::kable R code blocks to PreTeXt <table> XML elements."""

import re
import sys
from pathlib import Path

SOURCE_DIR = Path("/home/runner/work/rbook/rbook/pretext/source")

# Files to convert with whether they use CDATA or not
FILES_CONFIG = [
    ("ch5-descriptive-statistics.ptx", False),
    ("ch7-data-handling.ptx", False),
    ("ch12-chisquare.ptx", False),
    ("ch13-ttest.ptx", False),
    ("ch6-bayesian-statistics.ptx", True),
    ("ch-anova.ptx", True),
    ("ch5-factorial-anova.ptx", True),
]

_table_id_counter = [0]


def next_id(prefix="table-gen"):
    _table_id_counter[0] += 1
    return f"{prefix}-{_table_id_counter[0]}"


def extract_balanced(text, start, open_ch='(', close_ch=')'):
    """Extract balanced (open_ch ... close_ch) starting at text[start]."""
    assert text[start] == open_ch, f"Expected '{open_ch}' at {start}, got '{text[start]}'"
    depth = 0
    i = start
    in_str = False
    str_char = None
    while i < len(text):
        c = text[i]
        if in_str:
            if c == '\\' and i + 1 < len(text):
                i += 2
                continue
            elif c == str_char:
                in_str = False
        else:
            if c in ('"', "'"):
                in_str = True
                str_char = c
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1], i + 1
        i += 1
    return text[start:], len(text)


def split_top_level(text, delimiter=','):
    """Split text at top-level delimiter (not inside parens or strings)."""
    parts = []
    depth = 0
    in_str = False
    str_char = None
    cur = []
    i = 0
    while i < len(text):
        c = text[i]
        if in_str:
            cur.append(c)
            if c == '\\' and i + 1 < len(text):
                cur.append(text[i + 1])
                i += 2
                continue
            elif c == str_char:
                in_str = False
        else:
            if c in ('"', "'"):
                in_str = True
                str_char = c
                cur.append(c)
            elif c in ('(', '[', '{'):
                depth += 1
                cur.append(c)
            elif c in (')', ']', '}'):
                depth -= 1
                cur.append(c)
            elif c == delimiter and depth == 0:
                parts.append(''.join(cur).strip())
                cur = []
                i += 1
                continue
            else:
                cur.append(c)
        i += 1
    if cur:
        parts.append(''.join(cur).strip())
    return parts


def unescape_r_string(s):
    """Given an R string token (with surrounding quotes), return the value."""
    s = s.strip()
    if not s:
        return ''
    if s.upper() == 'NA' or s.upper() == 'NULL':
        return ''
    # Remove surrounding quotes
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1]
        # Handle R escape sequences
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                nc = s[i + 1]
                if nc == 'n':
                    result.append(' ')  # newline -> space
                elif nc == 't':
                    result.append(' ')  # tab -> space
                elif nc in ('v', 'b', 'r', 'f', 'a'):
                    pass  # skip other control chars
                elif nc == '\\':
                    result.append('\\')
                elif nc == "'":
                    result.append("'")
                elif nc == '"':
                    result.append('"')
                else:
                    result.append(nc)
                i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result).strip()
    # Not a string literal, return as-is (for numbers, NA, etc.)
    return s.strip()


def parse_r_vector(text):
    """Parse c(...) or just a value, return list of string values."""
    text = text.strip()
    if not text:
        return []
    # Handle c(...) form
    if text.startswith('c(') or text.startswith('c ('):
        # Extract content between parens
        paren_start = text.index('(')
        content, _ = extract_balanced(text, paren_start)
        inner = content[1:-1]  # strip parens
        parts = split_top_level(inner)
        result = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # Handle n:m range notation (e.g., 1:4)
            range_match = re.match(r'^(-?\d+):(-?\d+)$', p)
            if range_match:
                start_val = int(range_match.group(1))
                end_val = int(range_match.group(2))
                step = 1 if end_val >= start_val else -1
                result.extend(str(v) for v in range(start_val, end_val + step, step))
            else:
                result.append(unescape_r_string(p))
        return result
    # Single value
    return [unescape_r_string(text)]


def xml_escape_text(s):
    """Escape XML special characters in text content."""
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    return s


def convert_cell_value(val):
    """Convert a cell value string to PreTeXt XML content."""
    val = val.strip()
    if not val:
        return ''
    result = []
    i = 0
    while i < len(val):
        if val[i] == '$':
            # Look for a closing $
            j = val.find('$', i + 1)
            if j == -1:
                # No closing $ found - treat $ as a literal character and continue
                result.append('$')
                i += 1
            else:
                math_content = val[i + 1:j]
                # XML-escape content inside <m> too
                result.append(f'<m>{xml_escape_text(math_content)}</m>')
                i = j + 1
        elif val[i] == '`':
            j = val.find('`', i + 1)
            if j == -1:
                result.append(xml_escape_text(val[i:]))
                break
            else:
                code_content = val[i + 1:j]
                result.append(f'<c>{xml_escape_text(code_content)}</c>')
                i = j + 1
        elif val[i] == '*' and i + 1 < len(val) and val[i + 1] == '*':
            # Bold **text**
            j = val.find('**', i + 2)
            if j == -1:
                result.append(xml_escape_text(val[i:]))
                break
            bold_content = val[i + 2:j]
            result.append(f'<alert>{xml_escape_text(bold_content)}</alert>')
            i = j + 2
        elif val[i] == '*':
            # Italic *text*
            j = val.find('*', i + 1)
            if j == -1:
                result.append(xml_escape_text(val[i:]))
                break
            italic_content = val[i + 1:j]
            result.append(f'<em>{xml_escape_text(italic_content)}</em>')
            i = j + 1
        else:
            result.append(xml_escape_text(val[i]))
            i += 1
    return ''.join(result)


def parse_knitr_kable_args(r_code):
    """
    Parse the content of knitr::kable(...) - the full call minus 'knitr::kable'.
    Returns (headers, rows, caption) where headers is a list of strings,
    rows is a list of lists, caption is a string or None.
    """
    r_code = r_code.strip()
    # Find the opening paren of knitr::kable(
    if r_code.startswith('knitr::kable('):
        paren_start = len('knitr::kable')
    elif r_code.startswith('kable('):
        paren_start = len('kable')
    else:
        return None, None, None

    content, end = extract_balanced(r_code, paren_start)
    inner = content[1:-1]  # strip outer parens

    # Split into top-level arguments
    args = split_top_level(inner)

    if not args:
        return None, None, None

    # First arg is the data: rbind(...), data.frame(...), or tibble::tribble(...)
    data_arg = args[0].strip()

    # Remaining args: look for col.names, col.name, caption
    col_names = None
    caption = None
    for arg in args[1:]:
        arg = arg.strip()
        # col.names or col.name
        m = re.match(r'col\.names?\s*=\s*(c\(.*)', arg, re.DOTALL)
        if m:
            col_names = parse_r_vector(m.group(1).strip())
            continue
        m = re.match(r'caption\s*=\s*(.*)', arg, re.DOTALL)
        if m:
            caption = unescape_r_string(m.group(1).strip().rstrip(','))
            continue

    # Parse the data argument
    headers, rows = parse_data_arg(data_arg)

    # Override headers with col_names if provided
    if col_names is not None:
        headers = col_names

    return headers, rows, caption


def parse_data_arg(data_arg):
    """Parse the data argument of knitr::kable (rbind, data.frame, or tribble)."""
    data_arg = data_arg.strip()

    if data_arg.startswith('rbind('):
        return parse_rbind(data_arg)
    elif data_arg.startswith('data.frame('):
        return parse_dataframe(data_arg)
    elif 'tribble(' in data_arg:
        return parse_tribble(data_arg)
    else:
        return [], []


def parse_rbind(r_code):
    """Parse rbind(c(...), c(...), ...) returning ([], rows)."""
    paren_start = r_code.index('(')
    content, _ = extract_balanced(r_code, paren_start)
    inner = content[1:-1]

    # Split at top-level commas
    parts = split_top_level(inner)

    rows = []
    for part in parts:
        part = part.strip()
        if part.startswith('c('):
            row_vals = parse_r_vector(part)
            rows.append(row_vals)

    return [], rows  # No headers from rbind itself, col.names added later


def parse_dataframe(r_code):
    """Parse data.frame(col=c(...), ...) returning (col_names, rows)."""
    paren_start = r_code.index('(')
    content, _ = extract_balanced(r_code, paren_start)
    inner = content[1:-1]

    parts = split_top_level(inner)

    col_names = []
    columns = []  # list of lists of values

    for part in parts:
        part = part.strip()
        # Skip stringsAsFactors
        if part.startswith('stringsAsFactors'):
            continue
        # Named column: name = c(...)
        m = re.match(r'^[`\'"]?([^=`\'"]+?)[`\'"]?\s*=\s*(.*)', part, re.DOTALL)
        if m:
            col_name_raw = m.group(1).strip()
            col_val_raw = m.group(2).strip()
            # Clean backtick-quoted names
            if col_name_raw.startswith('`') and col_name_raw.endswith('`'):
                col_name_raw = col_name_raw[1:-1]
            # Replace dots with spaces in column names for display
            col_name_display = col_name_raw.replace('.', ' ')
            col_names.append(col_name_display)
            col_vals = parse_r_vector(col_val_raw)
            columns.append(col_vals)

    # Build rows from columns (transpose)
    if not columns:
        return col_names, []

    n_rows = max(len(c) for c in columns)
    rows = []
    for i in range(n_rows):
        row = []
        for col in columns:
            if i < len(col):
                row.append(col[i])
            else:
                row.append('')
        rows.append(row)

    return col_names, rows


def parse_tribble(r_code):
    """Parse tibble::tribble(~V1, ~V2, val1, val2, ...) returning (tilde_names, rows)."""
    # Find tribble(
    idx = r_code.index('tribble(')
    paren_start = idx + len('tribble')
    content, _ = extract_balanced(r_code, paren_start)
    inner = content[1:-1]

    parts = split_top_level(inner)

    tilde_names = []
    values = []

    for part in parts:
        part = part.strip()
        if part.startswith('~'):
            # Column tilde name
            name = part[1:].strip()
            # Remove quotes around name if any
            name = name.strip('"').strip("'")
            tilde_names.append(name)
        elif part:
            values.append(unescape_r_string(part))

    # Build rows
    n_cols = len(tilde_names)
    if n_cols == 0:
        return [], []

    rows = []
    for i in range(0, len(values), n_cols):
        row = values[i:i + n_cols]
        # Pad if short
        while len(row) < n_cols:
            row.append('')
        rows.append(row)

    return tilde_names, rows


def find_nearby_xref(text_lines, block_start_line, block_end_line, window=60):
    """
    Look for <xref ref="table-..."> in surrounding lines.
    Returns the ref value or None.
    """
    start = max(0, block_start_line - window)
    end = min(len(text_lines), block_end_line + window)

    candidates = []
    for i in range(start, end):
        line = text_lines[i]
        # Look for xref refs that start with "table-"
        for m in re.finditer(r'<xref\s+ref=["\']([^"\']*)["\']', line):
            ref = m.group(1)
            if ref.startswith('table-'):
                distance = abs(i - block_start_line)
                candidates.append((distance, ref))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    return None


def generate_pretext_table(xml_id, title, headers, rows, indent=''):
    """Generate PreTeXt table XML."""
    lines = []

    if xml_id:
        lines.append(f'{indent}<table xml:id="{xml_id}">')
    else:
        lines.append(f'{indent}<table>')

    if title:
        lines.append(f'{indent}  <title>{xml_escape_text(title)}</title>')

    lines.append(f'{indent}  <tabular halign="center">')

    # Header row
    if headers:
        lines.append(f'{indent}    <row header="yes" bottom="minor">')
        for i, h in enumerate(headers):
            cell_val = convert_cell_value(h)
            if i == 0:
                lines.append(f'{indent}      <cell halign="left">{cell_val}</cell>')
            else:
                lines.append(f'{indent}      <cell>{cell_val}</cell>')
        lines.append(f'{indent}    </row>')

    # Data rows
    for row in rows:
        lines.append(f'{indent}    <row>')
        for i, val in enumerate(row):
            cell_val = convert_cell_value(val)
            if i == 0:
                lines.append(f'{indent}      <cell halign="left">{cell_val}</cell>')
            else:
                lines.append(f'{indent}      <cell>{cell_val}</cell>')
        lines.append(f'{indent}    </row>')

    lines.append(f'{indent}  </tabular>')
    lines.append(f'{indent}</table>')

    return '\n'.join(lines)


def unescape_xml(s):
    """Unescape XML entities."""
    s = s.replace('&amp;', '&')
    s = s.replace('&lt;', '<')
    s = s.replace('&gt;', '>')
    s = s.replace('&quot;', '"')
    s = s.replace('&#39;', "'")
    return s


def find_program_blocks_with_kable(text, is_cdata):
    """
    Find all program blocks containing knitr::kable.
    Returns list of (start, end, r_code, leading_whitespace).
    start/end are character positions in text.
    """
    results = []

    if is_cdata:
        # Pattern: <program language="r">\n  <input><![CDATA[\n...knitr::kable...\n]]></input>\n</program>
        pattern = re.compile(
            r'(<program\s+language="r">\s*<input><!\[CDATA\[)(.*?)(\]\]></input>\s*</program>)',
            re.DOTALL
        )
        for m in pattern.finditer(text):
            r_code = m.group(2)
            if 'knitr::kable' in r_code:
                results.append((m.start(), m.end(), r_code, m.group(0)))
    else:
        # Pattern: <program language="r">\n  <input>\n...knitr::kable...\n  </input>\n</program>
        pattern = re.compile(
            r'(<program\s+language="r">\s*<input>)(.*?)(</input>\s*</program>)',
            re.DOTALL
        )
        for m in pattern.finditer(text):
            r_code_xml = m.group(2)
            if 'knitr::kable' in r_code_xml:
                # Unescape XML entities in R code
                r_code = unescape_xml(r_code_xml)
                results.append((m.start(), m.end(), r_code, m.group(0)))

    return results


def get_leading_whitespace(text, pos):
    """Get the leading whitespace of the line containing pos."""
    line_start = text.rfind('\n', 0, pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    line = text[line_start:pos + 1]
    m = re.match(r'^(\s*)', line)
    return m.group(1) if m else ''


def extract_all_kable_calls(r_code):
    """Extract all knitr::kable calls from R code, returning list of call strings."""
    calls = []
    i = 0
    while True:
        idx = r_code.find('knitr::kable(', i)
        if idx == -1:
            break
        # Find the balanced parens
        paren_start = idx + len('knitr::kable')
        call_content, end = extract_balanced(r_code, paren_start)
        full_call = 'knitr::kable' + call_content
        calls.append(full_call)
        i = end
    return calls


def convert_file(filepath, is_cdata):
    """Convert all knitr::kable blocks in a file."""
    filepath = Path(filepath)
    print(f"\n{'='*60}")
    print(f"Processing: {filepath.name}")

    text = filepath.read_text(encoding='utf-8')
    text_lines = text.splitlines()

    # Find all program blocks with knitr::kable
    blocks = find_program_blocks_with_kable(text, is_cdata)
    print(f"  Found {len(blocks)} program blocks with knitr::kable")

    if not blocks:
        return

    # Process in reverse order to preserve positions
    blocks_reversed = list(reversed(blocks))
    new_text = text

    for block_start, block_end, r_code, full_match in blocks_reversed:
        # Find line numbers for this block
        block_start_line = new_text[:block_start].count('\n')
        block_end_line = new_text[:block_end].count('\n')

        # Get indentation from the block
        indent = get_leading_whitespace(new_text, block_start)

        # Find nearby xref for table ID
        xref = find_nearby_xref(new_text.splitlines(), block_start_line, block_end_line)

        # Extract all knitr::kable calls from the R code
        kable_calls = extract_all_kable_calls(r_code)

        if not kable_calls:
            print(f"  WARNING: No kable calls found in block at line {block_start_line}")
            continue

        tables_xml = []
        xref_used = False

        for call_idx, call in enumerate(kable_calls):
            headers, rows, caption = parse_knitr_kable_args(call)

            if headers is None and rows is None:
                print(f"  WARNING: Could not parse kable call: {call[:100]}")
                continue

            # Determine xml:id
            if xref and not xref_used:
                xml_id = xref
                xref_used = True
            else:
                # Generate descriptive id
                xml_id = next_id(f"table-{filepath.stem.replace('-', '')[:15]}")

            print(f"  Table: xml:id={xml_id}, cols={len(headers) if headers else 0}, rows={len(rows)}, caption={caption[:50] if caption else None}")

            table_xml = generate_pretext_table(xml_id, caption, headers, rows, indent)
            tables_xml.append(table_xml)

        if tables_xml:
            replacement = '\n'.join(tables_xml)
            new_text = new_text[:block_start] + replacement + new_text[block_end:]

    filepath.write_text(new_text, encoding='utf-8')
    print(f"  Written: {filepath.name}")


def validate_xml(filepath):
    """Validate that the file is well-formed XML."""
    import xml.etree.ElementTree as ET
    try:
        ET.parse(filepath)
        print(f"  XML valid: {Path(filepath).name}")
        return True
    except ET.ParseError as e:
        print(f"  XML ERROR in {Path(filepath).name}: {e}")
        return False


def main():
    print("Converting knitr::kable blocks to PreTeXt tables")
    print("=" * 60)

    all_valid = True

    for filename, is_cdata in FILES_CONFIG:
        filepath = SOURCE_DIR / filename
        if not filepath.exists():
            print(f"WARNING: File not found: {filepath}")
            continue
        convert_file(filepath, is_cdata)

    print("\n" + "=" * 60)
    print("Validating XML...")
    for filename, _ in FILES_CONFIG:
        filepath = SOURCE_DIR / filename
        if filepath.exists():
            if not validate_xml(filepath):
                all_valid = False

    if all_valid:
        print("\nAll files are valid XML!")
    else:
        print("\nSome files have XML errors - please check.")


if __name__ == '__main__':
    main()
