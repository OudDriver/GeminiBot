import logging

import matplotlib.pyplot as plt
import regex
from matplotlib import rcParams

from packages.utilities.general_utils import generate_unique_file_name

logger = logging.getLogger(__name__)

def sanitize_latex(latex_text: str) -> str:
    """Remove any newlines.

    Args:
        latex_text: The LaTeX tag you want to sanitize.

    Returns:
        The sanitized text

    """
    return regex.sub(r"\n", " ", latex_text)


def render_latex(
        latex_string: str,
        preamble: str=r"\usepackage{amsmath}",
        padding: int=20,
        background_color: str="black",
        text_color: str="white",
        dpi: int=600,
        font_size: int=12,
) -> str | None:
    r"""Render a LaTeX string into a PNG image.

    The PNG file is automatically sent to the user.

    Args:
        latex_string (str): The LaTeX string to render.
        preamble (str, optional): The LaTeX preamble to use.
                                  Defaults to '\usepackage{amsmath}'.
        padding (int, optional): The padding around the rendered LaTeX, in pixels.
                                  Defaults to 20.
        background_color (str, optional): The background color of the image.
                                          Defaults to "black".
        text_color (str, optional): The color of the rendered LaTeX.
                                    Defaults to "white".
        dpi (int, optional): The resolution of the output image, in dots per inch.
                             Defaults to 300.
        font_size (int, optional): The font size of the rendered LaTeX.
                                   Defaults to 12.

    Returns:
        str: The file name of the rendered LaTeX image,
        or none if the LaTeX given is invalid.

    """
    try:
        latex_string = sanitize_latex(latex_string)

        rcParams["text.usetex"] = True
        rcParams["text.latex.preamble"] = preamble
        rcParams["font.size"] = font_size
        rcParams["font.family"] = "Computer Modern Roman"

        fig = plt.figure(figsize=(1, 1), dpi=1)
        text = fig.text(0, 0, latex_string, color=text_color)
        fig.canvas.draw()

        bbox = text.get_window_extent(fig.canvas.get_renderer())
        plt.close(fig)
        padding_inches = padding / dpi
        fig, ax = plt.subplots(
            figsize=(
                bbox.width / dpi + 2 * padding_inches,
                bbox.height / dpi + 2 * padding_inches,
            ),
            dpi=dpi,
        )
        fig.patch.set_facecolor(background_color)
        ax.text(
            0.5,
            0.5,
            latex_string,
            color=text_color,
            ha="center",
            va="center",
            fontsize=font_size,
        )
        ax.set_axis_off()
        file_name = fr".\temp\{generate_unique_file_name(r'png')}"

        fig.savefig(
            file_name,
            dpi=dpi,
            format="png",
            transparent=False,
            bbox_inches="tight",
            pad_inches=padding_inches,
            facecolor=background_color,
        )
        plt.close(fig)

        return file_name
    except RuntimeError:
        logger.exception("LaTeX rendering error!")
        return None

def split_tex(input_str: str) -> tuple[list[str], bool]:
    """Splits a string into normal parts and TeX math parts.

    This supports both inline math ($...$) and display math ($$...$$ or \[...\]).
    It also correctly handles multiline math content.

    Args:
        input_str: The input to split.

    Returns:
        A tuple consisting of:
        - A list of strings, alternating between normal text and TeX math.
        - A boolean indicating if any TeX math was found.
    """
    pattern = r"(\$\$.*?\$\$|\\\[.*?\\\]|\$.*?\$)"

    # We use regex.split to keep the delimiters
    parts = regex.split(pattern, input_str, flags=regex.DOTALL)

    non_empty_parts = [p for p in parts if p]
    has_tex = len(non_empty_parts) > 1 or (len(non_empty_parts) == 1 and non_empty_parts[0] != input_str)

    return non_empty_parts, has_tex

def check_tex(input_str: str) -> bool:
    """Checks if a string starts with $ and ends with $.

    Args:
        input_str: The input string to check.

    Returns:
        A boolean if that string is a
    """
    return input_str.startswith("$") and input_str.endswith("$")
