def _box(bbox):
    # flat bbox [x0, y0, x1, y1] ya easyocr ke 4 corner points, dono chalenge
    if bbox and isinstance(bbox[0], (int, float)):
        x0, y0, x1, y1 = bbox[:4]
        return x0, y0, x1, y1
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return min(xs), min(ys), max(xs), max(ys)


QUOTE_GLYPH_NOISE = {"66", "99", "“", "”", "\"", "''", "``"}


def _is_noise(text, conf, min_conf=0.30):
    t = text.strip()
    if not t or conf < min_conf:
        return True
    if t in QUOTE_GLYPH_NOISE:
        return True
    if not any(ch.isalnum() for ch in t) and len(t) <= 3:
        return True
    return False


def group_ocr_results(results, line_gap_ratio=0.9, min_conf=0.30):
    """
    results: [(bbox, text, conf), ...]
    return : [{"text", "bbox", "line_height", "line_count"}, ...]
    """
    items = []
    for bbox, text, conf in results:
        if _is_noise(text, conf, min_conf):
            continue
        x0, y0, x1, y1 = _box(bbox)
        items.append({"text": text.strip(), "x0": x0, "y0": y0, "x1": x1, "y1": y1})

    if not items:
        return []

    # Step A: same line ke tukde jodo
    items.sort(key=lambda i: (i["y0"] + i["y1"]) / 2)
    lines = []
    for it in items:
        placed = False
        for ln in lines:
            overlap = min(ln["y1"], it["y1"]) - max(ln["y0"], it["y0"])
            h = min(ln["y1"] - ln["y0"], it["y1"] - it["y0"])
            if h > 0 and overlap / h > 0.5:
                ln["parts"].append(it)
                ln["x0"] = min(ln["x0"], it["x0"])
                ln["y0"] = min(ln["y0"], it["y0"])
                ln["x1"] = max(ln["x1"], it["x1"])
                ln["y1"] = max(ln["y1"], it["y1"])
                placed = True
                break
        if not placed:
            lines.append({**it, "parts": [it]})

    for ln in lines:
        ln["parts"].sort(key=lambda p: p["x0"])
        ln["text"] = " ".join(p["text"] for p in ln["parts"])
        ln["h"] = ln["y1"] - ln["y0"]

    lines.sort(key=lambda l: l["y0"])

    # Step B: paas wali, same size wali lines ko paragraph banao
    blocks = []
    for ln in lines:
        if blocks:
            last = blocks[-1]["lines"][-1]
            gap = ln["y0"] - last["y1"]
            avg_h = (last["h"] + ln["h"]) / 2
            size_ratio = ln["h"] / last["h"] if last["h"] else 0
            x_overlap = min(last["x1"], ln["x1"]) - max(last["x0"], ln["x0"])
            center_diff = abs((last["x0"] + last["x1"]) / 2 - (ln["x0"] + ln["x1"]) / 2)
            aligned = x_overlap > 0 and (
                center_diff < avg_h * 3 or abs(last["x0"] - ln["x0"]) < avg_h * 1.5
            )
            if gap < avg_h * line_gap_ratio and 0.7 < size_ratio < 1.4 and aligned:
                blocks[-1]["lines"].append(ln)
                continue
        blocks.append({"lines": [ln]})

    out = []
    for b in blocks:
        ls = b["lines"]
        out.append({
            "text": " ".join(l["text"] for l in ls).strip(),
            "bbox": [
                min(l["x0"] for l in ls), min(l["y0"] for l in ls),
                max(l["x1"] for l in ls), max(l["y1"] for l in ls),
            ],
            "line_height": sum(l["h"] for l in ls) / len(ls),
            "line_count": len(ls),
            # NEW: keep every original line so the layout can be restored
            "lines": [
                {"text": l["text"], "bbox": [l["x0"], l["y0"], l["x1"], l["y1"]]}
                for l in ls
            ],
        })
    return out