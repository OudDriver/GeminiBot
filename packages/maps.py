from __future__ import annotations

import regex
from google.genai.types import (
    HarmBlockThreshold,
    HarmProbability,
)

SUPERSCRIPT_MAP: dict[str, str] = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶",
    "7": "⁷", "8": "⁸", "9": "⁹", "a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ",
    "e": "ᵉ", "f": "ᶠ", "g": "ᵍ", "h": "ʰ", "i": "ᶦ", "j": "ʲ", "k": "ᵏ",
    "l": "ˡ", "m": "ᵐ", "n": "ⁿ", "o": "ᵒ", "p": "ᵖ", "q": "۹", "r": "ʳ",
    "s": "ˢ", "t": "ᵗ", "u": "ᵘ", "v": "ᵛ", "w": "ʷ", "x": "ˣ", "y": "ʸ",
    "z": "ᶻ", "A": "ᴬ", "B": "ᴮ", "C": "ᶜ", "D": "ᴰ", "E": "ᴱ", "F": "ᶠ",
    "G": "ᴳ", "H": "ᴴ", "I": "ᴵ", "J": "ᴶ", "K": "ᴷ", "L": "ᴸ", "M": "ᴹ",
    "N": "ᴺ", "O": "ᴼ", "P": "ᴾ", "Q": "Q", "R": "ᴿ", "S": "ˢ", "T": "ᵀ",
    "U": "ᵁ", "V": "ⱽ", "W": "ᵂ", "X": "ˣ", "Y": "ʸ", "Z": "ᶻ", "+": "⁺",
    "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
}

SUBSCRIPT_MAP: dict[str, str] = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆",
    "7": "₇", "8": "₈", "9": "₉", "a": "ₐ", "b": "♭", "c": "꜀", "d": "ᑯ",
    "e": "ₑ", "f": "բ", "g": "₉", "h": "ₕ", "i": "ᵢ", "j": "ⱼ", "k": "ₖ",
    "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ", "q": "૧", "r": "ᵣ",
    "s": "ₛ", "t": "ₜ", "u": "ᵤ", "v": "ᵥ", "w": "w", "x": "ₓ", "y": "ᵧ",
    "z": "₂", "A": "ₐ", "B": "₈", "C": "C", "D": "D", "E": "ₑ", "F": "բ",
    "G": "G", "H": "ₕ", "I": "ᵢ", "J": "ⱼ", "K": "ₖ", "L": "ₗ", "M": "ₘ",
    "N": "ₙ", "O": "ₒ", "P": "ₚ", "Q": "Q", "R": "ᵣ", "S": "ₛ", "T": "ₜ",
    "U": "ᵤ", "V": "ᵥ", "W": "w", "X": "ₓ", "Y": "ᵧ", "Z": "Z", "+": "₊",
    "-": "₋", "=": "₌", "(": "₍", ")": "₎",
}

BLOCKED_CATEGORY: dict[str, list[HarmProbability]] = {
    "BLOCK_LOW_AND_ABOVE": [
        HarmProbability.LOW,
        HarmProbability.MEDIUM,
        HarmProbability.HIGH,
    ],
    "BLOCK_MEDIUM_AND_ABOVE": [HarmProbability.MEDIUM, HarmProbability.HIGH],
    "BLOCK_ONLY_HIGH": [HarmProbability.HIGH],
    "BLOCK_NONE": [],
}

HARM_BLOCK_CATEGORY: dict[str, HarmBlockThreshold] = {
    "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
    "OFF": HarmBlockThreshold.OFF,
}

HARM_PRETTY_NAME: dict[str, str] = {
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "Sexually Explicit",
    "HARM_CATEGORY_HATE_SPEECH": "Hate Speech",
    "HARM_CATEGORY_HARASSMENT": "Harassment",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "Dangerous Content",
    "HARM_CATEGORY_CIVIC_INTEGRITY": "Civil Integrity",
}
YOUTUBE_PATTERN = regex.compile(
    r"(?:https?:\/\/)?(?:youtu\.be\/|(?:www\.|m\.)"
    r"?youtube\.com\/(?:watch|v|embed)("
    r"?:\.php)?(?:\?.*v=|\/))([a-zA-Z0-9\_-]+)",
)
MAX_MESSAGE_LENGTH = 2000

# I couldn't fit all voices here since Discord has a hard limit
# For the amount of choices I can put.
TTS_VOICES = [
    {"name": "Zephyr", "personality": "Bright"},
    {"name": "Puck", "personality": "Upbeat"},
    {"name": "Charon", "personality": "Informative"},
    {"name": "Kore", "personality": "Firm"},
    {"name": "Fenrir", "personality": "Excitable"},
    {"name": "Leda", "personality": "Youthful"},
    {"name": "Aoede", "personality": "Breezy"},
    {"name": "Callirrhoe", "personality": "Easy-going"},
    {"name": "Enceladus", "personality": "Breathy"},
    {"name": "Iapetus", "personality": "Clear"},
    {"name": "Algieba", "personality": "Smooth"},
    {"name": "Erinome", "personality": "Clear"},
    {"name": "Algenib", "personality": "Gravelly"},
    {"name": "Rasalgethi", "personality": "Informative"},
    {"name": "Laomedeia", "personality": "Upbeat"},
    {"name": "Achernar", "personality": "Soft"},
    {"name": "Schedar", "personality": "Even"},
    {"name": "Gacrux", "personality": "Mature"},
    {"name": "Pulcherrima", "personality": "Forward"},
    {"name": "Achird", "personality": "Friendly"},
    {"name": "Zubenelgenubi", "personality": "Casual"},
    {"name": "Vindemiatrix", "personality": "Gentle"},
    {"name": "Sadachbia", "personality": "Lively"},
    {"name": "Sadaltager", "personality": "Knowledgeable"},
    {"name": "Sulafat", "personality": "Warm"},
]

IMAGE_GENERATION_MODELS = ["gemini-2.5-flash-image-preview"]
