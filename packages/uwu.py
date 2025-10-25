from __future__ import annotations

import logging
import random
from copy import deepcopy
from typing import ClassVar, TypedDict

import regex
import validators
from regex import Pattern

BREAK_PUNCTUATION: set[str] = {".", ",", "!", "?", ";"}

logger = logging.getLogger(__name__)


class UwuifierSpacesConfig(TypedDict, total=False):
    """Configuration for space-based uwuifications."""

    faces: float
    actions: float
    stutters: float


class UwuifierConfig(TypedDict, total=False):
    """Configuration for the Uwuifier."""

    words: float
    spaces: UwuifierSpacesConfig
    exclamations: float


class Uwuifier:
    """A class to transform text into an uwuified version.

    Applies various transformations like word substitutions, adding faces/actions,
    stuttering, and modifying exclamations based on configurable probabilities.
    All randomness is derived from a seed generated from the input text,
    ensuring deterministic output for the same input.
    """

    _DEFAULT_CONFIG: ClassVar[dict[str, float | dict[str, float]]] = {
        "words": 0.2,
        "spaces": {
            "faces": 0.08,
            "actions": 0.05,
            "stutters": 0.1,
        },
        "exclamations": 0.8,
    }

    _FACES: ClassVar[list[str]] = [
        "(・\\`ω´・)",
        ";;w;;",
        "OwO",
        "UwU",
        ">w<",
        "^w^",
        "ÚwÚ",
        "^-^",
        ":3",
        "x3",
    ]
    _EXCLAMATIONS: ClassVar[list[str]] = ["!?", "?!!", "?!?1", "!!11", "?!?!", "1!!1!"]
    _ACTIONS: ClassVar[list[str]] = [
        r"\*blushes\*",
        r"\*whispers to self\*",
        r"\*cries\*",
        r"\*screams\*",
        r"\*sweats\*",
        r"\*twerks\*",
        r"\*runs away\*",
        r"\*screeches\*",
        r"\*walks away\*",
        r"\*begins interpretative dance\*",
        r"\*looks at you\*",
        r"\*notices buldge\*",
        r"\*starts twerking\*",
        r"\*huggles tightly\*",
        r"\*boops your nose\*",
        r"\*drops armful of books\*",
    ]

    _UWU_MAP_PATTERNS: ClassVar[list[tuple[Pattern[str], str]]] = [
        (regex.compile(r"[rl]", regex.IGNORECASE), "w"),
        (regex.compile(r"n([aeiou])", regex.IGNORECASE), r"ny\1"),
        (regex.compile(r"ove", regex.IGNORECASE), "uv"),
    ]

    _EXCLAMATION_PATTERN: Pattern[str] = regex.compile(r"[?!]+$")

    def __init__(
        self, config: UwuifierConfig | None = None,
    ) -> None:
        """Initialize the Uwuifier with optional custom configuration."""
        cfg = deepcopy(self._DEFAULT_CONFIG)
        if config:
            # Update top-level keys first
            cfg.update({k: v for k, v in config.items() if k != "spaces"})

            # Handle the 'spaces' key with explicit validation
            if "spaces" in config:
                spaces_config = config["spaces"]
                if not isinstance(spaces_config, dict):
                    # If 'spaces' exists but isn't a dict, raise an error.
                    msg = (
                        f"The 'spaces' key in the configuration must be a dictionary, "
                        f"but got type {type(spaces_config).__name__}."
                    )
                    raise TypeError(msg)

                cfg["spaces"].update(spaces_config)

        # Use properties for validation during assignment
        self.words_modifier = float(cfg.get("words", 0.0))
        self.spaces_modifier = {k: float(v) for k, v in cfg.get("spaces", {}).items()}
        self.exclamations_modifier = float(cfg.get("exclamations", 0.0))

    @staticmethod
    def _is_word_skippable(word: str) -> bool:
        """Check if a word should be skipped for transformations.

        It checks that if the word starts with @ or is a URI.

        Args:
            word: The word to check.

        Returns:
            True if the word should be skipped, False otherwise.
        """
        if word.startswith("@"):
            return True

        return bool(validators.url(word))

    # --- Private Transformation Methods (now using a shared RNG) ---
    def _uwuify_word(self, word: str, rng: random.Random) -> str:
        """Applies uwu_map regex substitutions to a single word."""
        for pattern, replacement in self._UWU_MAP_PATTERNS:
            if rng.random() < self.words_modifier:
                word = pattern.sub(replacement, word)
        return word

    def _uwuify_exclamation(self, word: str, rng: random.Random) -> str:
        """Replaces trailing exclamation/question marks."""
        match = self._EXCLAMATION_PATTERN.search(word)
        if match and rng.random() < self.exclamations_modifier:
            word_stem = word[: match.start()]
            return word_stem + rng.choice(self._EXCLAMATIONS)
        return word

    def _add_space_element(self, word: str, rng: random.Random) -> str:
        """Probabilistically adds a face, action, or stutter after a word."""
        choices = []
        weights = []

        # Build weighted list of possible actions
        prob_face = self.spaces_modifier.get("faces", 0.0)
        if self._FACES and prob_face > 0:
            choices.append("face")
            weights.append(prob_face)

        prob_action = self.spaces_modifier.get("actions", 0.0)
        if self._ACTIONS and prob_action > 0:
            choices.append("action")
            weights.append(prob_action)

        prob_stutter = self.spaces_modifier.get("stutters", 0.0)
        if prob_stutter > 0 and word:
            choices.append("stutter")
            weights.append(prob_stutter)

        # If no actions are possible, return early
        if not choices:
            return word

        # Add the 'do nothing' option
        choices.append("none")
        weights.append(1.0 - sum(weights))

        # Choose an action
        action = rng.choices(choices, weights=weights)[0]

        if action == "face":
            return f"{word} {rng.choice(self._FACES)}"
        if action == "action":
            return f"{word} {rng.choice(self._ACTIONS)}"
        if action == "stutter":
            stutter_count = rng.randint(1, 2)
            return f"{word[0]}-" * stutter_count + word

        # "none" case
        return word

    # --- Public API Method ---
    def uwuify(self, text: str) -> str:
        """Apply all uwuification transformations to the input text."""
        if not isinstance(text, str):
            msg = "text is not string!"
            raise TypeError(msg)

        if not text.strip():
            return text

        # Seed a single RNG for the entire sentence for deterministic results
        rng = random.Random(text) # For all future devs, the seed must be `text`.
        words = text.split(" ")
        final_words = []

        for i, word in enumerate(words):
            if not word:
                final_words.append(word)
                continue

            # Skip transformations for special cases like URIs and mentions
            if self._is_word_skippable(word):
                final_words.append(word)
                continue

            processed_word = self._uwuify_word(word, rng)
            processed_word = self._uwuify_exclamation(processed_word, rng)

            next_word = words[i + 1] if i + 1 < len(words) else None
            can_add_space_element = (
                word not in BREAK_PUNCTUATION
                and next_word is not None
                and next_word not in BREAK_PUNCTUATION
            )

            if can_add_space_element:
                processed_word = self._add_space_element(processed_word, rng)

            final_words.append(processed_word)

        return " ".join(final_words)

    def uwuify_sentence(self, sentence: str) -> str:
        """Alias for the uwuify method."""
        return self.uwuify(sentence)
