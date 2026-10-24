"""Regenerate the simple book icon with Pillow (optional artwork tool)."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'android/app/src/main/res'
BLUE = '#1f5fbf'


def icon(size, foreground=False):
    image = Image.new('RGBA', (512, 512), (0, 0, 0, 0) if foreground else BLUE)
    draw = ImageDraw.Draw(image)
    # Keep the book inside Android's adaptive-icon safe region.
    draw.polygon([(136, 162), (238, 176), (250, 188), (250, 350), (238, 338), (136, 324)], fill='white')
    draw.polygon([(262, 188), (274, 176), (376, 162), (376, 324), (274, 338), (262, 350)], fill='white')
    for y in (215, 250, 285):
        draw.line([(156, y), (228, y + 10)], fill=BLUE, width=7)
        draw.line([(284, y + 10), (356, y)], fill=BLUE, width=7)
    return image.resize((size, size), Image.Resampling.LANCZOS)


for density, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
    folder = RES / f'mipmap-{density}'
    icon(size).save(folder / 'ic_launcher.png')
    icon(size).save(folder / 'ic_launcher_round.png')
    icon(round(size * 108 / 48), True).save(folder / 'ic_launcher_foreground.png')
for path in RES.glob('drawable*/splash.png'):
    with Image.open(path) as original:
        width, height = original.size
    splash = Image.new('RGB', (width, height), BLUE)
    symbol = icon(min(width, height) // 2)
    splash.paste(symbol, ((width-symbol.width)//2, (height-symbol.height)//2), symbol)
    splash.save(path)
icon(512).convert('RGB').save(ROOT / 'mobile/play-icon.png')
