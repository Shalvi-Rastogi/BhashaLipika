# import re
# import unicodedata

# # ---------------- Config ----------------
# DEBUG = True
# MAX_GAP = 2

# TAG_RE = re.compile(
#     r"<(?:script|style)\b[^>]*>.*?</(?:script|style)\s*>|<!--.*?-->|<![^>]*>|<[^>]+>",
#     re.DOTALL | re.IGNORECASE)
# VOID = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "wbr"}

# BLOCK = {"address", "article", "aside", "blockquote", "body", "br", "dd", "details", "div", "dl",
#          "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
#          "h6", "head", "header", "hr", "html", "li", "main", "nav", "ol", "option", "p", "pre",
#          "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "title", "tr", "ul"}

# _SENT_END_NAMES = ("FULL STOP", "QUESTION MARK", "EXCLAMATION MARK", "DANDA")

# _aligner = None

# def _get_aligner():
#     global _aligner
#     if _aligner is None:
#         from simalign import SentenceAligner
#         _aligner = SentenceAligner(model="bert", token_type="bpe", matching_methods="i", device="cpu")
#     return _aligner

# # ---------------- Punctuation & Parsing Helpers ----------------
# def _is_p(ch): return unicodedata.category(ch).startswith("P")

# def _norm(word):
#     i, j = 0, len(word)
#     while i < j and _is_p(word[i]): i += 1
#     while j > i and _is_p(word[j - 1]): j -= 1
#     return word[i:j].lower()

# def _is_punct(word): return bool(word) and _norm(word) == ""

# def _attaches_left(word):
#     return _is_punct(word) and unicodedata.category(word[0]) in ("Po", "Pe", "Pf")

# def _is_sentence_end(word):
#     ch = word[-1]
#     return unicodedata.category(ch) == "Po" and any(k in unicodedata.name(ch, "") for k in _SENT_END_NAMES)

# def _layout_ws(ws):
#     return ws if "\n" in ws else ""

# def _parse_html(html):
#     words, tags, anchors, stack, breaks, word_seq = [], [], [], [], set(), []
#     seq, last, pos = [0], [None], 0

#     def next_seq():
#         seq[0] += 1
#         return seq[0]

#     def add_words(text):
#         for w in text.split():
#             words.append(w)
#             word_seq.append(seq[0])
#             for t in stack: t["words"].append(len(words) - 1)

#     def handle_gap(gap):
#         if gap.strip():
#             left, right = gap[:len(gap) - len(gap.lstrip())], gap[len(gap.rstrip()):]
#             trail, lead = _layout_ws(left), _layout_ws(right)
#         else:
#             trail = lead = _layout_ws(gap)
#         if last[0] is not None: last[0][0][last[0][1]] = trail
#         add_words(gap)
#         return lead

#     def new_anchor(html_str, lead, at, order_seq):
#         a = {"at": at, "html": html_str, "lead": lead, "trail": "", "seq": order_seq}
#         anchors.append(a)
#         last[0] = (a, "trail")
#         return a

#     counter = 0
#     for m in TAG_RE.finditer(html):
#         lead = handle_gap(html[pos:m.start()])
#         pos, raw = m.end(), m.group(0)

#         nm = re.match(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9:-]*)", raw)
#         if not nm or raw.lower().startswith(("<script", "<style")):
#             new_anchor(raw, lead, len(words), next_seq())
#             continue

#         closing, name = nm.group(1) == "/", nm.group(2).lower()
#         if closing:
#             for k in range(len(stack) - 1, -1, -1):
#                 if stack[k]["name"] == name:
#                     t = stack.pop(k)
#                     t["close"], t["close_lead"], t["close_seq"] = raw, lead, next_seq()
#                     last[0] = (t, "close_trail")
#                     if name in BLOCK: breaks.add(len(words))
#                     if t["words"]: tags.append(t)
#                     else: new_anchor(t["open"] + raw, t["open_lead"], t["start"], t["open_seq"])
#                     break
#             else: new_anchor(raw, lead, len(words), next_seq())
#         elif name in VOID or raw.endswith("/>"):
#             if name in BLOCK: breaks.add(len(words))
#             new_anchor(raw, lead, len(words), next_seq())
#         else:
#             counter += 1
#             t = {"name": name, "open": raw, "close": "", "words": [], "start": len(words), "order": counter,
#                  "parent": stack[-1] if stack else None, "open_lead": lead, "open_trail": "", "open_seq": next_seq(),
#                  "close_lead": "", "close_trail": "", "close_seq": 0}
#             stack.append(t)
#             last[0] = (t, "open_trail")
#             if name in BLOCK: breaks.add(len(words))

#     handle_gap(html[pos:])
#     for t in stack:
#         if t["words"]: tags.append(t)
#         else:
#             a = new_anchor(t["open"], t["open_lead"], t["start"], t["open_seq"])
#             a["trail"] = t["open_trail"]
#     return words, tags, anchors, breaks, word_seq

# def _is_ancestor(a, t):
#     p = t["parent"]
#     while p is not None:
#         if p is a: return True
#         p = p["parent"]
#     return False

# # ---------------- Alignment & Range Logic ----------------
# def _split_sentences(words, breaks=()):
#     chunks, start = [], 0
#     for i, w in enumerate(words):
#         if _is_sentence_end(w) or (i + 1) in breaks:
#             chunks.append((start, i + 1))
#             start = i + 1
#     if start < len(words): chunks.append((start, len(words)))
#     return chunks

# def _align(src_chunk, tgt_chunk):
#     try:
#         return list(_get_aligner().get_word_aligns(src_chunk, tgt_chunk)["itermax"])
#     except Exception as error:
#         print(f"[HTML] SimAlign failed ({error})")
#         return []

# def _raw_range(t, s2t, n_src, n_tgt):
#     """
#     NEW FIX: Contextual Neighbor Fallback + Dense Core Clustering
#     """
#     idx = sorted({j for i in t["words"] for j in s2t.get(i, [])})
    
#     if not idx:
#         # Fallback: Tag is completely unaligned. Look at its neighbors instead of math.
#         b_tgt, a_tgt = -1, n_tgt
#         for i in range(t["words"][0] - 1, -1, -1):
#             if s2t.get(i): b_tgt = max(s2t[i]); break
#         for i in range(t["words"][-1] + 1, n_src):
#             if s2t.get(i): a_tgt = min(s2t[i]); break
        
#         if b_tgt != -1 and a_tgt != n_tgt and a_tgt > b_tgt:
#             mid = (b_tgt + a_tgt) // 2
#             return mid, mid
#         elif b_tgt != -1: return min(b_tgt + 1, n_tgt - 1), min(b_tgt + 1, n_tgt - 1)
#         elif a_tgt != n_tgt: return max(a_tgt - 1, 0), max(a_tgt - 1, 0)
#         return None

#     # Clustering: Drop stray verbs/words that jumped to the end of the sentence
#     clusters = [[idx[0]]]
#     for j in idx[1:]:
#         if j - clusters[-1][-1] > MAX_GAP: clusters.append([j])
#         else: clusters[-1].append(j)

#     # Pick the cluster covering the most words (The Core Phrase)
#     best = max(clusters, key=len)
#     return best[0], best[-1]

# def _clamp(r, lo, hi):
#     s, e = max(r[0], lo), min(r[1], hi)
#     if s > e: s = e = min(max(r[0], lo), hi)
#     return s, e

# def _overlap(a, b): return a[0] <= b[1] and b[0] <= a[1]

# def _resolve_siblings(children, ranges):
#     for x in range(len(children)):
#         for y in range(x + 1, len(children)):
#             A, B = children[x], children[y]
#             ra, rb = ranges[A["order"]], ranges[B["order"]]
#             if not _overlap(ra, rb): continue
#             ca, cb = sum(ra) / 2, sum(rb) / 2
#             L, R = (A, B) if ca <= cb else (B, A)
#             (ls, le), (rs, re_) = ranges[L["order"]], ranges[R["order"]]
#             if ls < rs: ranges[L["order"]] = (ls, rs - 1)
#             elif re_ > le: ranges[R["order"]] = (le + 1, re_)

# def _covered_by_other(j, t, tags, ranges):
#     for o in tags:
#         if o is t or _is_ancestor(o, t) or _is_ancestor(t, o): continue
#         if ranges[o["order"]][0] <= j <= ranges[o["order"]][1]: return True
#     return False

# def _absorb_sentence_final_words(tags, ranges, chunk_map, src_words, tgt_words, t2s):
#     for a, b, off, n in chunk_map:
#         tgt_idx = [j for j in range(off, off + n) if not _is_punct(tgt_words[j])]
#         src_idx = [i for i in range(a, b) if not _is_punct(src_words[i])]
#         if not tgt_idx or not src_idx: continue
#         last_tgt, last_src = tgt_idx[-1], src_idx[-1]

#         for t in tags:
#             if t["words"][-1] != last_src: continue
#             s, e = ranges[t["order"]]
#             if e >= last_tgt: continue
#             between = range(e + 1, last_tgt + 1)
#             if all(_is_punct(tgt_words[j]) or not t2s.get(j) for j in between) \
#                     and not _covered_by_other(last_tgt, t, tags, ranges):
#                 ranges[t["order"]] = (s, last_tgt)

# def _tag_items(tag_html, lead, trail):
#     items = []
#     if lead: items.append(("ws", lead))
#     items.append(("tag", tag_html))
#     if trail: items.append(("ws", trail))
#     return items

# def _emit(result, items, attach_left=False):
#     if not items: return result
#     if result and not result[-1].isspace() and items[0][0] != "ws" and not attach_left: result += " "
#     for kind, text in items:
#         if kind == "ws" and result.endswith(text): continue
#         result += text
#     return result

# # ---------------- Main ----------------
# def translate_html(html_content, translate_func, src_lang, tgt_lang):
#     if not html_content or not html_content.strip(): return html_content
#     src_words, tags, anchors, breaks, word_seq = _parse_html(html_content)
#     if not src_words: return html_content

#     tgt_words, s2t, t2s, chunk_map = [], {}, {}, []
#     for a, b in _split_sentences(src_words, breaks):
#         src_chunk = src_words[a:b]
#         try: translated = translate_func(" ".join(src_chunk), src_lang, tgt_lang)
#         except Exception as error:
#             print(f"[HTML] Translation failed: {error}")
#             return html_content
#         if not translated: return html_content

#         tgt_chunk = translated.split()
#         off = len(tgt_words)
#         tgt_words.extend(tgt_chunk)
#         chunk_map.append((a, b, off, len(tgt_chunk)))

#         pairs = _align(src_chunk, tgt_chunk)
#         for i, j in pairs:
#             if _is_punct(src_chunk[i]) != _is_punct(tgt_chunk[j]): continue
#             s2t.setdefault(a + i, []).append(off + j)
#             t2s.setdefault(off + j, []).append(a + i)

#     n_src, n_tgt = len(src_words), len(tgt_words)
#     if n_tgt == 0: return html_content

#     ranges = {}
#     for t in tags:
#         r = _raw_range(t, s2t, n_src, n_tgt)
#         if r is None: r = (0, 0)
#         ranges[t["order"]] = r

#     for t in sorted(tags, key=lambda x: x["order"], reverse=True):
#         p = t["parent"]
#         if p is not None:
#             pr, cr = ranges[p["order"]], ranges[t["order"]]
#             ranges[p["order"]] = (min(pr[0], cr[0]), max(pr[1], cr[1]))

#     for node in [None] + sorted(tags, key=lambda x: x["order"]):
#         children = [c for c in tags if c["parent"] is node]
#         if node is not None:
#             lo, hi = ranges[node["order"]]
#             for c in children: ranges[c["order"]] = _clamp(ranges[c["order"]], lo, hi)
#         _resolve_siblings(children, ranges)

#     _absorb_sentence_final_words(tags, ranges, chunk_map, src_words, tgt_words, t2s)

#     for t in sorted(tags, key=lambda x: x["order"], reverse=True):
#         p = t["parent"]
#         if p is not None:
#             pr, cr = ranges[p["order"]], ranges[t["order"]]
#             ranges[p["order"]] = (min(pr[0], cr[0]), max(pr[1], cr[1]))

#     before, after = {}, {}
#     for t in tags:
#         s, e = ranges[t["order"]]
#         before.setdefault(s, []).append((t["open_seq"], _tag_items(t["open"], t["open_lead"], t["open_trail"])))
#         if t["close"]: after.setdefault(e, []).append((t["close_seq"], _tag_items(t["close"], t["close_lead"], t["close_trail"])))

#     real = []
#     for t in tags:
#         real.append((t["open_seq"], "open", t))
#         if t["close"]: real.append((t["close_seq"], "close", t))
#     real.sort(key=lambda x: x[0])

#     for a in anchors:
#         nxt = next((r for r in real if r[0] > a["seq"]), None)
#         i = a["at"]
#         word_first = i < len(src_words)
#         if nxt is not None and (not word_first or nxt[0] <= word_seq[i]):
#             s, e = ranges[nxt[2]["order"]]
#             slot = (before, s) if nxt[1] == "open" else (after, e)
#         elif word_first:
#             k = i
#             while k < len(src_words) and not s2t.get(k): k += 1
#             slot = (before, min(s2t[k]) if k < len(src_words) else n_tgt)
#         else: slot = (before, n_tgt)
#         slot[0].setdefault(slot[1], []).append((a["seq"], _tag_items(a["html"], a["lead"], a["trail"])))

#     result = ""
#     for idx in range(n_tgt + 1):
#         pre = [it for _, items in sorted(before.get(idx, []), key=lambda x: x[0]) for it in items]
#         if idx == n_tgt:
#             result = _emit(result, pre)
#             break
#         post = [it for _, items in sorted(after.get(idx, []), key=lambda x: x[0]) for it in items]
#         word = tgt_words[idx]
#         result = _emit(result, pre + [("word", word)] + post, attach_left=_attaches_left(word))

#     lead_ws = html_content[:len(html_content) - len(html_content.lstrip())]
#     trail_ws = html_content[len(html_content.rstrip()):]
#     return lead_ws + result.strip() + trail_ws
import re
import unicodedata

# ---------------- Config ----------------
DEBUG = True
MAX_GAP = 2

TAG_RE = re.compile(
    r"<(?:script|style)\b[^>]*>.*?</(?:script|style)\s*>|<!--.*?-->|<![^>]*>|<[^>]+>",
    re.DOTALL | re.IGNORECASE)
VOID = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "wbr"}

BLOCK = {"address", "article", "aside", "blockquote", "body", "br", "dd", "details", "div", "dl",
         "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
         "h6", "head", "header", "hr", "html", "li", "main", "nav", "ol", "option", "p", "pre",
         "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "title", "tr", "ul"}

_SENT_END_NAMES = ("FULL STOP", "QUESTION MARK", "EXCLAMATION MARK", "DANDA")

_aligner = None

def _get_aligner():
    global _aligner
    if _aligner is None:
        from simalign import SentenceAligner
        _aligner = SentenceAligner(model="bert", token_type="bpe", matching_methods="i", device="cpu")
    return _aligner

# ---------------- Punctuation & Parsing Helpers ----------------
def _is_p(ch): return unicodedata.category(ch).startswith("P")

def _norm(word):
    i, j = 0, len(word)
    while i < j and _is_p(word[i]): i += 1
    while j > i and _is_p(word[j - 1]): j -= 1
    return word[i:j].lower()

def _is_punct(word): return bool(word) and _norm(word) == ""

def _attaches_left(word):
    return _is_punct(word) and unicodedata.category(word[0]) in ("Po", "Pe", "Pf")

def _is_sentence_end(word):
    ch = word[-1]
    return unicodedata.category(ch) == "Po" and any(k in unicodedata.name(ch, "") for k in _SENT_END_NAMES)

def _layout_ws(ws):
    return ws if "\n" in ws else ""

def _parse_html(html):
    words, tags, anchors, stack, breaks, word_seq = [], [], [], [], set(), []
    seq, last, pos = [0], [None], 0

    def next_seq():
        seq[0] += 1
        return seq[0]

    def add_words(text):
        for w in text.split():
            words.append(w)
            word_seq.append(seq[0])
            for t in stack: t["words"].append(len(words) - 1)

    def handle_gap(gap):
        if gap.strip():
            left, right = gap[:len(gap) - len(gap.lstrip())], gap[len(gap.rstrip()):]
            trail, lead = _layout_ws(left), _layout_ws(right)
        else:
            trail = lead = _layout_ws(gap)
        if last[0] is not None: last[0][0][last[0][1]] = trail
        add_words(gap)
        return lead

    def new_anchor(html_str, lead, at, order_seq):
        a = {"at": at, "html": html_str, "lead": lead, "trail": "", "seq": order_seq}
        anchors.append(a)
        last[0] = (a, "trail")
        return a

    counter = 0
    for m in TAG_RE.finditer(html):
        lead = handle_gap(html[pos:m.start()])
        pos, raw = m.end(), m.group(0)

        nm = re.match(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9:-]*)", raw)
        if not nm or raw.lower().startswith(("<script", "<style")):
            new_anchor(raw, lead, len(words), next_seq())
            continue

        closing, name = nm.group(1) == "/", nm.group(2).lower()
        if closing:
            for k in range(len(stack) - 1, -1, -1):
                if stack[k]["name"] == name:
                    t = stack.pop(k)
                    t["close"], t["close_lead"], t["close_seq"] = raw, lead, next_seq()
                    last[0] = (t, "close_trail")
                    if name in BLOCK: breaks.add(len(words))
                    if t["words"]: tags.append(t)
                    else: new_anchor(t["open"] + raw, t["open_lead"], t["start"], t["open_seq"])
                    break
            else: new_anchor(raw, lead, len(words), next_seq())
        elif name in VOID or raw.endswith("/>"):
            if name in BLOCK: breaks.add(len(words))
            new_anchor(raw, lead, len(words), next_seq())
        else:
            counter += 1
            t = {"name": name, "open": raw, "close": "", "words": [], "start": len(words), "order": counter,
                 "parent": stack[-1] if stack else None, "open_lead": lead, "open_trail": "", "open_seq": next_seq(),
                 "close_lead": "", "close_trail": "", "close_seq": 0}
            stack.append(t)
            last[0] = (t, "open_trail")
            if name in BLOCK: breaks.add(len(words))

    handle_gap(html[pos:])
    for t in stack:
        if t["words"]: tags.append(t)
        else:
            a = new_anchor(t["open"], t["open_lead"], t["start"], t["open_seq"])
            a["trail"] = t["open_trail"]
    return words, tags, anchors, breaks, word_seq

def _is_ancestor(a, t):
    p = t["parent"]
    while p is not None:
        if p is a: return True
        p = p["parent"]
    return False

# ---------------- Alignment & Range Logic ----------------
def _split_sentences(words, breaks=()):
    chunks, start = [], 0
    for i, w in enumerate(words):
        if _is_sentence_end(w) or (i + 1) in breaks:
            chunks.append((start, i + 1))
            start = i + 1
    if start < len(words): chunks.append((start, len(words)))
    return chunks

def _align(src_chunk, tgt_chunk):
    try:
        return list(_get_aligner().get_word_aligns(src_chunk, tgt_chunk)["itermax"])
    except Exception as error:
        print(f"[HTML] SimAlign failed ({error})")
        return []

def _raw_range(t, s2t, n_src, n_tgt):
    idx = sorted({j for i in t["words"] for j in s2t.get(i, [])})
    
    if not idx:
        # Fallback: Tag is completely unaligned. Look at its neighbors instead of math.
        b_tgt, a_tgt = -1, n_tgt
        for i in range(t["words"][0] - 1, -1, -1):
            if s2t.get(i): b_tgt = max(s2t[i]); break
        for i in range(t["words"][-1] + 1, n_src):
            if s2t.get(i): a_tgt = min(s2t[i]); break
        
        if b_tgt != -1 and a_tgt != n_tgt and a_tgt > b_tgt:
            mid = (b_tgt + a_tgt) // 2
            return mid, mid
        elif b_tgt != -1: return min(b_tgt + 1, n_tgt - 1), min(b_tgt + 1, n_tgt - 1)
        elif a_tgt != n_tgt: return max(a_tgt - 1, 0), max(a_tgt - 1, 0)
        return None

    # THE FIX: Block-level tags (`<h1>`, `<p>`, `<div>` etc.) should NEVER be clustered or shrunk. 
    # They MUST wrap their entire content, no matter the word gap.
    if t["name"] in BLOCK:
        return idx[0], idx[-1]

    # For inline tags (`<b>`, `<i>`, `<em>`), use a much safer/larger gap tolerance (5 instead of 2)
    clusters = [[idx[0]]]
    for j in idx[1:]:
        if j - clusters[-1][-1] > 5: 
            clusters.append([j])
        else: 
            clusters[-1].append(j)

    best = max(clusters, key=len)
    return best[0], best[-1]

def _clamp(r, lo, hi):
    s, e = max(r[0], lo), min(r[1], hi)
    if s > e: s = e = min(max(r[0], lo), hi)
    return s, e

def _overlap(a, b): return a[0] <= b[1] and b[0] <= a[1]

def _resolve_siblings(children, ranges):
    for x in range(len(children)):
        for y in range(x + 1, len(children)):
            A, B = children[x], children[y]
            ra, rb = ranges[A["order"]], ranges[B["order"]]
            if not _overlap(ra, rb): continue
            ca, cb = sum(ra) / 2, sum(rb) / 2
            L, R = (A, B) if ca <= cb else (B, A)
            (ls, le), (rs, re_) = ranges[L["order"]], ranges[R["order"]]
            if ls < rs: ranges[L["order"]] = (ls, rs - 1)
            elif re_ > le: ranges[R["order"]] = (le + 1, re_)

def _covered_by_other(j, t, tags, ranges):
    for o in tags:
        if o is t or _is_ancestor(o, t) or _is_ancestor(t, o): continue
        if ranges[o["order"]][0] <= j <= ranges[o["order"]][1]: return True
    return False

def _absorb_sentence_final_words(tags, ranges, chunk_map, src_words, tgt_words, t2s):
    for a, b, off, n in chunk_map:
        tgt_idx = [j for j in range(off, off + n) if not _is_punct(tgt_words[j])]
        src_idx = [i for i in range(a, b) if not _is_punct(src_words[i])]
        if not tgt_idx or not src_idx: continue
        last_tgt, last_src = tgt_idx[-1], src_idx[-1]

        for t in tags:
            if t["words"][-1] != last_src: continue
            s, e = ranges[t["order"]]
            if e >= last_tgt: continue
            between = range(e + 1, last_tgt + 1)
            if all(_is_punct(tgt_words[j]) or not t2s.get(j) for j in between) \
                    and not _covered_by_other(last_tgt, t, tags, ranges):
                ranges[t["order"]] = (s, last_tgt)

def _tag_items(tag_html, lead, trail):
    items = []
    if lead: items.append(("ws", lead))
    items.append(("tag", tag_html))
    if trail: items.append(("ws", trail))
    return items

def _emit(result, items, attach_left=False):
    if not items: return result
    if result and not result[-1].isspace() and items[0][0] != "ws" and not attach_left: result += " "
    for kind, text in items:
        if kind == "ws" and result.endswith(text): continue
        result += text
    return result

# ---------------- Main ----------------
def translate_html(html_content, translate_func, src_lang, tgt_lang):
    if not html_content or not html_content.strip(): return html_content
    src_words, tags, anchors, breaks, word_seq = _parse_html(html_content)
    if not src_words: return html_content

    tgt_words, s2t, t2s, chunk_map = [], {}, {}, []
    for a, b in _split_sentences(src_words, breaks):
        src_chunk = src_words[a:b]
        try: translated = translate_func(" ".join(src_chunk), src_lang, tgt_lang)
        except Exception as error:
            print(f"[HTML] Translation failed: {error}")
            return html_content
        if not translated: return html_content

        tgt_chunk = translated.split()
        off = len(tgt_words)
        tgt_words.extend(tgt_chunk)
        chunk_map.append((a, b, off, len(tgt_chunk)))

        pairs = _align(src_chunk, tgt_chunk)
        for i, j in pairs:
            if _is_punct(src_chunk[i]) != _is_punct(tgt_chunk[j]): continue
            s2t.setdefault(a + i, []).append(off + j)
            t2s.setdefault(off + j, []).append(a + i)

    n_src, n_tgt = len(src_words), len(tgt_words)
    if n_tgt == 0: return html_content

    ranges = {}
    for t in tags:
        r = _raw_range(t, s2t, n_src, n_tgt)
        if r is None: r = (0, 0)
        ranges[t["order"]] = r

    for t in sorted(tags, key=lambda x: x["order"], reverse=True):
        p = t["parent"]
        if p is not None:
            pr, cr = ranges[p["order"]], ranges[t["order"]]
            ranges[p["order"]] = (min(pr[0], cr[0]), max(pr[1], cr[1]))

    for node in [None] + sorted(tags, key=lambda x: x["order"]):
        children = [c for c in tags if c["parent"] is node]
        if node is not None:
            lo, hi = ranges[node["order"]]
            for c in children: ranges[c["order"]] = _clamp(ranges[c["order"]], lo, hi)
        _resolve_siblings(children, ranges)

    _absorb_sentence_final_words(tags, ranges, chunk_map, src_words, tgt_words, t2s)

    for t in sorted(tags, key=lambda x: x["order"], reverse=True):
        p = t["parent"]
        if p is not None:
            pr, cr = ranges[p["order"]], ranges[t["order"]]
            ranges[p["order"]] = (min(pr[0], cr[0]), max(pr[1], cr[1]))

    before, after = {}, {}
    for t in tags:
        s, e = ranges[t["order"]]
        before.setdefault(s, []).append((t["open_seq"], _tag_items(t["open"], t["open_lead"], t["open_trail"])))
        if t["close"]: after.setdefault(e, []).append((t["close_seq"], _tag_items(t["close"], t["close_lead"], t["close_trail"])))

    real = []
    for t in tags:
        real.append((t["open_seq"], "open", t))
        if t["close"]: real.append((t["close_seq"], "close", t))
    real.sort(key=lambda x: x[0])

    for a in anchors:
        nxt = next((r for r in real if r[0] > a["seq"]), None)
        i = a["at"]
        word_first = i < len(src_words)
        if nxt is not None and (not word_first or nxt[0] <= word_seq[i]):
            s, e = ranges[nxt[2]["order"]]
            slot = (before, s) if nxt[1] == "open" else (after, e)
        elif word_first:
            k = i
            while k < len(src_words) and not s2t.get(k): k += 1
            slot = (before, min(s2t[k]) if k < len(src_words) else n_tgt)
        else: slot = (before, n_tgt)
        slot[0].setdefault(slot[1], []).append((a["seq"], _tag_items(a["html"], a["lead"], a["trail"])))

    result = ""
    for idx in range(n_tgt + 1):
        pre = [it for _, items in sorted(before.get(idx, []), key=lambda x: x[0]) for it in items]
        if idx == n_tgt:
            result = _emit(result, pre)
            break
        post = [it for _, items in sorted(after.get(idx, []), key=lambda x: x[0]) for it in items]
        word = tgt_words[idx]
        result = _emit(result, pre + [("word", word)] + post, attach_left=_attaches_left(word))

    lead_ws = html_content[:len(html_content) - len(html_content.lstrip())]
    trail_ws = html_content[len(html_content.rstrip()):]
    return lead_ws + result.strip() + trail_ws