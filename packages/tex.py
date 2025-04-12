import regex
import logging
from packages.utils import generate_unique_file_name

import matplotlib.pyplot as plt
from matplotlib import rcParams

def sanitize_latex(latex_text: str) -> str:
    de_tag = regex.sub(r'<tex>|</tex>', "", latex_text)
    whitespaced = regex.sub(r'\n', ' ', de_tag)

    return whitespaced

def render_latex(latex_string: str, preamble: str=r'\usepackage{amsmath}', padding: int=20, background_color: str="white",
                 text_color: str="black", dpi: int=300, font_size: int=12):
    r"""Renders a LaTeX string into a PNG image. The PNG file is automatically sent to the user.

    Args:
        latex_string (str): The LaTeX string to render.
        preamble (str, optional): The LaTeX preamble to use. Defaults to '\usepackage{amsmath}'.
        padding (int, optional): The padding around the rendered LaTeX, in pixels. Defaults to 20.
        background_color (str, optional): The background color of the image. Defaults to "white".
        text_color (str, optional): The color of the rendered LaTeX. Defaults to "black".
        dpi (int, optional): The resolution of the output image, in dots per inch. Defaults to 300.
        font_size (int, optional): The font size of the rendered LaTeX. Defaults to 12.

    Returns:
        str: The file name of the rendered LaTeX image, or the RuntimeError if the latex_string is invalid.
    """
    try:
        latex_string = sanitize_latex(latex_string)

        rcParams['text.usetex'] = True
        rcParams['text.latex.preamble'] = preamble
        rcParams['font.size'] = font_size
        rcParams['font.family'] = "Computer Modern Roman"

        fig = plt.figure(figsize=(1, 1), dpi=1)
        text = fig.text(0, 0, latex_string, color=text_color)
        fig.canvas.draw()  
        
        bbox = text.get_window_extent(fig.canvas.get_renderer())
        plt.close(fig)
        padding_inches = padding / dpi
        fig, ax = plt.subplots(figsize=(bbox.width / dpi + 2 * padding_inches,
                                        bbox.height / dpi + 2 * padding_inches), dpi=dpi)
        fig.patch.set_facecolor(background_color)
        ax.text(0.5, 0.5, latex_string, color=text_color, ha='center', va='center', fontsize=font_size)
        ax.set_axis_off()
        file_name = fr".\temp\{generate_unique_file_name(r'png')}"
        
        fig.savefig(
            file_name,
            dpi=dpi,
            format='png',
            transparent=False,
            bbox_inches='tight',
            pad_inches=padding_inches,
            facecolor=background_color
        )
        plt.close(fig)

        return file_name
    except RuntimeError as e:
        logging.error(f"LaTeX rendering error! {e}")
        return None

def split_tex(input_str: str) -> list:
    return regex.split(r'(<tex>.*?</tex>)', input_str)

def check_tex(input_str: str) -> bool:
    return input_str.startswith("<tex>") and input_str.endswith("</tex>")
