from PIL import Image, ImageDraw, ImageFont

font_path = r"C:\Windows\Fonts\Nirmala.ttc"

image = Image.new(
    "RGB",
    (800, 200),
    "white"
)

draw = ImageDraw.Draw(image)

font = ImageFont.truetype(
    font_path,
    50,
    index=0
)

draw.text(
    (30, 50),
    "नमस्ते दुनिया।",
    fill="black",
    font=font
)

image.save(
    "hindi_font_test.png"
)

print("Hindi font test completed.")