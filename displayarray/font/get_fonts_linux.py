import subprocess


def list_fonts_linux():
    result = subprocess.run(['fc-list', '--format=%{file}\n'], stdout=subprocess.PIPE)
    fonts = result.stdout.decode().strip().split('\n')
    return fonts


def get_default_font_linux():
    result = subprocess.run(['fc-match', '--format=%{file}\n'], stdout=subprocess.PIPE)
    default_font = result.stdout.decode().strip()
    return default_font


if __name__ == '__main__':
    fonts = list_fonts_linux()
    print("Available fonts on Linux:")
    for font in fonts:
        print(font)

    default_font = get_default_font_linux()
    print("Default font on Linux:", default_font)
