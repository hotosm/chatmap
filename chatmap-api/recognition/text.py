"""Texts made plain, so a word matches however it is typed."""
import re
import unicodedata


# What is written in more than one way, folded to one way, so a word matches however it is typed
FOLDED = str.maketrans({
    # Arabic letters typed in other ways: alef wasla, alef maqsura, ta marbuta, and the
    # Persian yeh and keheh some keyboards give
    "ٱ": "ا", "ى": "ي", "ة": "ه", "ی": "ي", "ک": "ك",
    # The digits of Arabic and Persian, as the ones of the roads and hours most people type
    **{chr(0x0660 + digit): str(digit) for digit in range(10)},
    **{chr(0x06F0 + digit): str(digit) for digit in range(10)},
    # The geresh and gershayim of Hebrew, as the quotes many type instead, and its final
    # letters as the others, so a word matches when it is the start of a longer one
    "׳": "'", "״": '"', "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ",
    # The tatweel that stretches Arabic words, and the marks that only say where text joins or runs
    "ـ": None, "\u200c": None, "\u200d": None, "\u200e": None, "\u200f": None,
})


# A letter written more than once in a row, as in a word stretched to stress it; digits are not, 100 is not 10
REPEATED = re.compile(r"([^\W\d_])\1+")


def plain(text: str) -> str:
    """
    A text without case nor accents, to compare it: without the vowel marks
    and hamza of Arabic nor the niqqud of Hebrew, with the letters and digits
    written in more than one way folded to one (see FOLDED), and a letter
    repeated in a row once ("cerrrrado" as "cerrado", both as "cerado").
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    unmarked = "".join(char for char in decomposed if not unicodedata.combining(char)).translate(FOLDED)
    return REPEATED.sub(r"\1", unmarked)
