import os
if os.name == 'nt':
    from get_fonts_windows import get_default_font_windows as get_default_font, list_fonts_windows as list_fonts
else:
    from get_fonts_linux import get_default_font_linux as get_default_font, list_fonts_linux as list_fonts

def print_fonts():
    fonts = list_fonts()
    print("Available fonts:")
    for font in fonts:
        print(font)

if __name__ == '__main__':
    print_fonts()

    default_font = get_default_font()
    print("Default font:", default_font)
