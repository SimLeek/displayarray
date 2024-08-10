from PIL import ImageFont, ImageDraw, Image
import numpy as np
from displayarray.font.get_fonts import get_default_font
from fontTools.ttLib import TTFont
import os

def load_font(ttf_path=None, font_size=32):
    if ttf_path is None:
        ttf_path = get_default_font()
    font = ImageFont.truetype(ttf_path, font_size)
    return font

def get_available_characters(font_path):
    if font_path is None:
        font_path = get_default_font()
    font = TTFont(font_path)
    available_chars = []
    #for char_code in range(0x110000):
    for table in font['cmap'].tables:
        #if char_code in table.cmap.keys():
        for key, value in table.cmap.items():
            available_chars.append(chr(key))
    return available_chars

def render_glyphs(font, characters):
    glyphs = {}
    max_width = max_height = 0
    for char in characters:
        bbox = font.getbbox(char)
        size = bbox[2], bbox[3]
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
    res = num_glyphs*max_width*max_height
    atlas_height = int(np.ceil(np.sqrt(res)))
    atlas_width = int(np.floor(np.sqrt(res)))
    atlas_image = Image.new('L', (atlas_width, atlas_height))

    # note: tried rectpack here. It took forever. Not really worth the slight compression.

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
                              characters=None):
    font = load_font(ttf_path, font_size)
    if characters is None:
        characters = get_available_characters(ttf_path)
    glyphs, max_width, max_height = render_glyphs(font, characters)
    atlas_image, glyph_data = create_texture_atlas(glyphs, max_width, max_height)
    #metadata = generate_glyph_metadata(glyph_data, atlas_image.width, atlas_image.height)

    # Convert atlas image to a format suitable for OpenGL (e.g., numpy array)
    atlas_texture = np.array(atlas_image)

    return atlas_texture, glyph_data


def get_or_create_font_npz(ttf_path=None, font_size=14, characters=None):
    # Get the directory of the current script
    script_dir = os.path.dirname(__file__)

    # Generate the filename based on the font name and size
    if ttf_path is None:
        ttf_path = get_default_font()
    font_name = os.path.basename(ttf_path).split('.')[0]
    npz_filename = f"{font_name}_{font_size}.npz"
    npz_filepath = os.path.join(script_dir, npz_filename)

    # Check if the .npz file exists
    if os.path.exists(npz_filepath):
        return npz_filepath

    atlas_texture, metadata = create_font_texture_atlas(ttf_path=ttf_path, font_size=font_size,
                                                        characters=characters)

    # If not, create the .npz file with the atlas texture and metadata
    np.savez_compressed(npz_filepath, atlas_texture=atlas_texture, metadata=metadata)

    return npz_filepath


if __name__ == '__main__':

    #get_or_create_font_npz()

    atlas_texture, metadata = create_font_texture_atlas(ttf_path=None, font_size=24,
                                                        characters=None)

    print("Texture atlas created with metadata:", metadata)

    from displayarray import DirectDisplay
    d = DirectDisplay()

    d.imshow("font", atlas_texture)
    while not d.window.is_closing:
        d.update()