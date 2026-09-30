import fitz, json

f = fitz.Font(fontfile=r"app/assets/fonts/Nirmala.ttf")
print(f.has_glyph(ord("क")))   # True hona chahiye

d = json.load(open("outputs/sample_translated_hi.json", encoding="utf-8"))
t = d["pages"][0]["elements"][0]["translated_text"]
print(repr(t), [hex(ord(c)) for c in t[:8]])