from PIL import ImageFont, ImageDraw, Image
import numpy as np
from get_fonts import get_default_font


def load_font(ttf_path=None, font_size=32):
    if ttf_path is None:
        ttf_path = get_default_font()
    font = ImageFont.truetype(ttf_path, font_size)
    return font


def render_glyphs(font, characters):
    glyphs = {}
    max_width = max_height = 0
    for char in characters:
        bbox = font.getbbox(char)
        size = bbox[2]-bbox[0], bbox[3]
        #size = font.size, font.font.height
        image = Image.new('L', size=size)
        draw = ImageDraw.Draw(image)
        draw.text((-bbox[0], 0), char, font=font, fill=255)
        glyphs[char] = image
        max_width = max(max_width, size[0])
        max_height = max(max_height, size[1])
    return glyphs, max_width, max_height


def create_texture_atlas(glyphs, max_width, max_height):
    num_glyphs = len(glyphs)
    h = int(np.ceil(np.sqrt(num_glyphs)))
    w = int(np.floor(np.sqrt(num_glyphs)))
    atlas_width = max_width * w
    atlas_height = max_height * h
    atlas_image = Image.new('L', (atlas_width, atlas_height))

    x_offset = 0
    y_offset = 0
    row_height = 0
    glyph_data = {}
    for char, glyph in glyphs.items():
        if x_offset+glyph.width> atlas_width:
            x_offset = 0
            y_offset += row_height
            row_height = 0
            if y_offset> atlas_height:
                raise ValueError("max_width and max_height are too small to contain all characters")
        atlas_image.paste(glyph, (x_offset, y_offset))
        glyph_data[char] = (x_offset, y_offset, glyph.width, glyph.height)
        x_offset += glyph.width
        if glyph.height> row_height:
            row_height = glyph.height


    return atlas_image.crop((0,0,atlas_width, y_offset+row_height)), glyph_data


def generate_glyph_metadata(glyph_data, atlas_width, atlas_height):
    metadata = {}
    for char, (x, y, width, height) in glyph_data.items():
        metadata[char] = {
            'uv_coords': (x / atlas_width, y / atlas_height, (x + width) / atlas_width, (y + height) / atlas_height),
            'size': (width, height)
        }
    return metadata


def create_font_texture_atlas(ttf_path=None, font_size=12,
                              characters=[chr(i) for i in range(256)]):
    font = load_font(ttf_path, font_size)
    glyphs, max_width, max_height = render_glyphs(font, characters)
    atlas_image, glyph_data = create_texture_atlas(glyphs, max_width, max_height)
    metadata = generate_glyph_metadata(glyph_data, atlas_image.width, atlas_image.height)

    # Convert atlas image to a format suitable for OpenGL (e.g., numpy array)
    atlas_texture = np.array(atlas_image)

    return atlas_texture, metadata


if __name__ == '__main__':
    atlas_texture, metadata = create_font_texture_atlas(font_size=32,
                                                        characters=[chr(i) for i in range(256)])
    print("Texture atlas created with metadata:", metadata)

    from displayarray import DirectDisplay
    d = DirectDisplay()

    d.imshow("font", atlas_texture)
    while not d.window.is_closing:
        d.update()