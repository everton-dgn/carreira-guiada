"""Retouch bounded regions of the original artwork without regenerating its design."""

import io
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/assets'
# Recoverable originals, including the two personal-feature illustrations.
SOURCE_COMMIT = 'f9b0beb416a021818a3e3e692c18a6e2903cc3c0'
NAMES = ('perfil-projetos-banner', 'propostas-comparacao-banner',
         'meu-plano-ilustrado', 'minha-evolucao-ilustrada',
         'plano-carreira-banner')


def region_mask(image, region, predicate):
    """Select matching pixels only inside a bounded region of the original."""
    mask = Image.new('L', image.size)
    pixels, source = mask.load(), image.load()
    for y in range(region[1], min(region[3], image.height)):
        for x in range(region[0], min(region[2], image.width)):
            pixels[x, y] = 255 if predicate(*source[x, y]) else 0
    return mask


def blue_glow(image, region):
    """Soften blue lighting while leaving the light paper and typography intact."""
    mask = region_mask(image, region, lambda r, g, b: r < 65 and g < 145 and b > 85 and b > g * 1.25)
    mask = mask.filter(ImageFilter.GaussianBlur(8))
    calmer = ImageEnhance.Brightness(ImageEnhance.Color(image).enhance(.85)).enhance(.78)
    return Image.composite(calmer, image, mask)


def solid_titles(image, region):
    """Flatten the interiors of existing glyphs, keeping their antialiased edges."""
    colors = [('#f3f7ff', lambda r, g, b: min(r, g, b) > 150),
              ('#00ddec', lambda r, g, b: r < 100 and g > 125 and b > 145)]
    for color, predicate in colors:
        mask = region_mask(image, region, predicate).filter(ImageFilter.MinFilter(3))
        image = Image.composite(Image.new('RGB', image.size, color), image, mask)
    return image


def proposal_glow(image):
    """Use a continuous blue-light correction without a blurred selection edge."""
    pixels = image.load()
    for y in range(image.height):
        for x in range(1000, image.width):
            r, g, b = pixels[x, y]
            strength = min(1, (x - 1000) / 160)
            strength *= min(1, max(0, (b - r) / 100))
            strength *= min(1, max(0, (150 - r) / 100))
            strength *= min(1, max(0, (b - 60) / 100))
            pixels[x, y] = tuple(round(c * (1 - .16 * strength)) for c in (r, g, b))
    return image


def title_spacing(image):
    """Reduce the existing career headline by 7 percent to clear the notebook."""
    bounds = (100, 220, 1215, 423)
    layer = image.crop(bounds)
    mask = region_mask(layer, (0, 0, layer.width, layer.height), lambda r, g, b: g > 135 and b > 150)
    background = Image.new('RGB', layer.size)
    pixels = background.load()
    for x in range(layer.width):
        above = image.getpixel((bounds[0] + x, bounds[1] - 8))
        below = image.getpixel((bounds[0] + x, bounds[3] + 8))
        for y in range(layer.height):
            ratio = y / (layer.height - 1)
            pixels[x, y] = tuple(round(above[c] * (1 - ratio) + below[c] * ratio) for c in range(3))
    background = background.filter(ImageFilter.GaussianBlur(16))
    # Reuse fine texture from a blank source region, without carrying its objects.
    grain = image.crop((100, 520, 1215, 723))
    smooth = grain.filter(ImageFilter.GaussianBlur(6))
    pixels = background.load()
    for y in range(layer.height):
        for x in range(layer.width):
            detail, low = grain.getpixel((x, y)), smooth.getpixel((x, y))
            pixels[x, y] = tuple(max(0, min(255, pixels[x, y][c] + max(-3, min(3, detail[c] - low[c])))) for c in range(3))
    feather = mask.filter(ImageFilter.MaxFilter(41)).filter(ImageFilter.GaussianBlur(3))
    clear = Image.composite(background, layer, feather)
    lettering = solid_titles(layer, (0, 0, layer.width, layer.height))
    lettering.putalpha(mask)
    lettering = lettering.resize((round(layer.width * .93), round(layer.height * .93)), Image.Resampling.LANCZOS)
    clear.paste(lettering, (0, round(layer.height * .035)), lettering)
    image.paste(clear, bounds[:2])
    return image


def retouch(name, image):
    """Apply only the reviewed adjustment assigned to the named source asset."""
    if name == 'perfil-projetos-banner':
        return blue_glow(image, (0, 0, 1450, 260))
    if name == 'propostas-comparacao-banner':
        return proposal_glow(image)
    if name == 'meu-plano-ilustrado':
        mask = region_mask(image, (900, 200, 1900, 793), lambda r, g, b: r < 70 and 35 < g < 145 and b > 175)
        image = Image.composite(ImageEnhance.Brightness(image).enhance(.77), image, mask)
        return solid_titles(image, (35, 265, 1040, 475))
    if name == 'minha-evolucao-ilustrada':
        return solid_titles(image, (35, 200, 950, 540))
    if name == 'plano-carreira-banner':
        return title_spacing(image)
    raise ValueError('Unknown source artwork.')


def main():
    """Read immutable originals from Git and write new, reproducible derivatives."""
    for name in NAMES:
        try:
            source = subprocess.run(['git', 'show', f'{SOURCE_COMMIT}:docs/assets/{name}.png'],
                                    cwd=ROOT, check=True, capture_output=True).stdout
        except subprocess.CalledProcessError as error:
            raise SystemExit('O histórico precisa conter o commit de origem indicado neste gerador.') from error
        original = Image.open(io.BytesIO(source)).convert('RGB')
        result = retouch(name, original.copy())
        if result.size != original.size:
            raise ValueError('The retouch must preserve the source resolution.')
        if ImageChops.difference(result, original).getbbox() is None:
            raise ValueError('The expected retouch did not change the image.')
        result.save(OUT / f'{name}-refinado.png')
        print(f'{name}: resolução e composição preservadas')


if __name__ == '__main__':
    main()
