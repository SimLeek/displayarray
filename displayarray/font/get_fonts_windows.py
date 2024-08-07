import glob
import os

def list_fonts_windows():
    font_dir = r'C:\Windows\Fonts'
    fonts = []
    fonts.extend(glob.glob(os.path.join(font_dir, '*.ttf')))
    fonts.extend(glob.glob(os.path.join(font_dir, '*.otf')))
    return fonts


def get_default_font_windows():
    return r'C:\Windows\Fonts\arial.ttf'


if __name__ == '__main__':
    fonts = list_fonts_windows()
    print("Available fonts on Windows:")
    for font in fonts:
        print(font)

    default_font = get_default_font_windows()
    print("Default font on Windows:", default_font)
