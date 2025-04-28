from __future__ import annotations

import logging
import random
from typing import ClassVar

import regex
from regex import Pattern

# --- Constants ---
MAX_UINT32 = 0xffffffff
URI_PATTERN: Pattern[str] = regex.compile(r"^(https?|ftp)://[^\s/$.?#].[^\s]*$")
BREAK_PUNCTUATION: set[str] = {".", ",", "!", "?", ";"}

logger = logging.getLogger(__name__)

# --- Seed Class ---
class Seed:
    """A simple pseudo-random number generator seeded by a given value.

    Ensures that the same input seed always produces the same sequence
    of random numbers, constrained within a 32-bit unsigned integer range.
    """

    def __init__(self, seed_val: object) -> None:
        """Initializes the Seed object and the random number generator.

        Args:
            seed_val: The value used to seed the random number generator.
                      It will be hashed and constrained to MAX_UINT32.
        """
        self.seed: int = hash(seed_val) & MAX_UINT32
        self.rng: random.Random = random.Random(self.seed)

    def random(self) -> float:
        """Return the next random floating point number in the range [0.0, 1.0)."""
        return self.rng.random()

    def random_int(self, min_val: int, max_val: int) -> int:
        """Return a random integer N such that min_val <= N <= max_val."""
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        if min_val == max_val:
            return min_val
        return self.rng.randint(min_val, max_val)


# --- Uwuifier Class ---
class Uwuifier:
    """A class to transform text into an "uwuified" version.

    Applies various transformations like word substitutions, adding faces/actions,
    stuttering, and modifying exclamations based on configurable probabilities.
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

    # Use built-in list type hint
    _FACES: ClassVar[list[str]] = [
        "(・`ω´・)", ";;w;;", "OwO", "UwU", ">w<", "^w^", "ÚwÚ", "^-^", ":3", "x3",  # noqa: RUF001
    ]
    _EXCLAMATIONS: ClassVar[list[str]] = ["!?", "?!!", "?!?1", "!!11", "?!?!", "1!!1!"]
    _ACTIONS: ClassVar[list[str]] = [
        r"\*blushes\*", r"\*whispers to self\*", r"\*cries\*", r"\*screams\*",
        r"\*sweats\*", r"\*twerks\*", r"\*runs away\*", r"\*screeches\*",
        r"\*walks away\*", r"\*begins interpretative dance\*", r"\*looks at you\*",
        r"\*notices buldge\*", r"\*starts twerking\*", r"\*huggles tightly\*",
        r"\*boops your nose\*", r"\*drops armful of books\*",
    ]

    # Use built-in list and tuple type hints
    _UWU_MAP_PATTERNS: ClassVar[list[tuple[Pattern[str], str]]] = [
        (regex.compile(r"[rl]", regex.IGNORECASE), "w"),
        (regex.compile(r"n([aeiou])", regex.IGNORECASE), r"ny\1"),
        (regex.compile(r"ove", regex.IGNORECASE), "uv"),
    ]

    _EXCLAMATION_PATTERN: Pattern[str] = regex.compile(r"[?!]+$")


    def __init__(
        self,
        # Use | None for optional types
        config: dict[str, float | dict[str, float]] | None = None,
    ) -> None:
        """Initialize the Uwuifier with optional custom configuration.

        Args:
            config: A dictionary to override default probabilities. Expected keys:
                    'words': Probability (0-1) of applying word substitutions.
                    'spaces': Dictionary with probabilities (0-1) for 'faces',
                              'actions', and 'stutters' insertions in spaces.
                              The sum of these should be <= 1.
                    'exclamations': Probability (0-1) of modifying exclamations.
                    If None or keys are missing, uses defaults.
        """
        effective_config = self._DEFAULT_CONFIG.copy()
        if config:
            # Update defaults with provided config, handling nested dict for spaces
            effective_config.update({k: v for k, v in config.items() if k != "spaces"})
            if (
                "spaces" in config
                and isinstance(config["spaces"], dict)
            ):
                if "spaces" not in effective_config or not isinstance(
                    effective_config["spaces"], dict,
                ):
                    # Initialize if missing or wrong type
                    effective_config["spaces"] = {}
                # Update only the space probabilities provided
                effective_config["spaces"].update(config["spaces"])


        # Use setters for validation and assignment
        words_mod = effective_config.get("words")
        spaces_mod = effective_config.get("spaces")
        excl_mod = effective_config.get("exclamations")

        if isinstance(words_mod, (int, float)):
            self.words_modifier = float(words_mod)
        else:
            self.words_modifier = float(self._DEFAULT_CONFIG["words"])
            logger.warning("Invalid type for 'words' modifier, using default.")

        if isinstance(spaces_mod, dict):
            valid_spaces_mod = {
                k: float(v) for k, v in spaces_mod.items()
                if isinstance(v, (int, float))
            }
            invalid_keys = set(spaces_mod.keys()) - set(valid_spaces_mod.keys())
            if invalid_keys:
                logger.warning(
                    f"Invalid types for space modifiers {invalid_keys}, ignoring.",
                )
            self.spaces_modifier = valid_spaces_mod
        else:
            # Need to ensure the default is copied correctly if used as fallback
            default_spaces = self._DEFAULT_CONFIG["spaces"]
            self.spaces_modifier = default_spaces.copy()
            logger.warning("Invalid type for 'spaces' modifier, using default.")


        if isinstance(excl_mod, (int, float)):
            self.exclamations_modifier = float(excl_mod)
        else:
            self.exclamations_modifier = float(self._DEFAULT_CONFIG["exclamations"])
            logger.warning("Invalid type for 'exclamations' modifier, using default.")

        # Store pre-compiled patterns/lists for easy access
        self.faces = self._FACES
        self.exclamations = self._EXCLAMATIONS
        self.actions = self._ACTIONS
        self.uwu_map = self._UWU_MAP_PATTERNS

    # --- Static helper methods ---
    @staticmethod
    def _is_at(word: str) -> bool:
        """Check if a word starts with the '@' symbol (like a mention)."""
        return word.startswith("@")

    @staticmethod
    def _is_uri(word: str) -> bool:
        """Check if a word is a URI using the pre-compiled pattern."""
        return URI_PATTERN.match(word) is not None

    @staticmethod
    def _is_break(word: str) -> bool:
        """Check if a word is a common punctuation mark acting as a sentence break."""
        return word in BREAK_PUNCTUATION

    # --- Properties with validation ---
    @property
    def words_modifier(self) -> float:
        """Probability (0-1) of applying word substitutions."""
        return self._words_modifier

    @words_modifier.setter
    def words_modifier(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            msg = "words_modifier value must be between 0.0 and 1.0"
            raise ValueError(msg)
        self._words_modifier = value

    @property
    # Use built-in dict type hint
    def spaces_modifier(self) -> dict[str, float]:
        """Dictionary with probabilities (0-1) for space insertions."""
        return self._spaces_modifier

    @spaces_modifier.setter
    # Use built-in dict type hint
    def spaces_modifier(self, value: dict[str, float]) -> None:
        """Set the probabilities for inserting elements into spaces.

        Args:
            value: A dictionary mapping element types ('faces', 'actions',
                   'stutters') to their insertion probabilities (0.0 to 1.0).

        Raises:
            ValueError: If any probability is outside [0, 1] or the sum > 1.0.
        """
        sum_val = 0.0
        for key, prob in value.items():
            if not 0.0 <= prob <= 1.0:
                 msg = (
                     f"Probability for '{key}' must be between 0.0 and 1.0, "
                     f"got {prob}"
                 )
                 raise ValueError(msg)
            sum_val += prob

        if sum_val > 1.0:
            msg = (
                f"Sum of spaces_modifier probabilities cannot exceed 1.0, "
                f"got {sum_val}"
            )
            raise ValueError(msg)
        self._spaces_modifier = value


    @property
    def exclamations_modifier(self) -> float:
        """Probability (0-1) of modifying exclamation marks."""
        return self._exclamations_modifier

    @exclamations_modifier.setter
    def exclamations_modifier(self, value: float) -> None:
        """Set the probability for modifying exclamation marks."""
        if not 0.0 <= value <= 1.0:
            msg = "exclamations_modifier value must be between 0.0 and 1.0"
            raise ValueError(msg)
        self._exclamations_modifier = value

    def _uwuify_word(self, word: str, seed_prefix: object) -> str:
        """Applies uwu_map regex substitutions to a single word based on probability."""
        if self._is_at(word) or self._is_uri(word):
            return word

        uwuified_word = word
        # Use unique, deterministic seed for each rule application on the word
        base_seed_val = f"{seed_prefix}_{word}"
        for i, (pattern, replacement) in enumerate(self.uwu_map):
            rule_seed = Seed(f"{base_seed_val}_{i}")
            if rule_seed.random() < self.words_modifier:
                uwuified_word = pattern.sub(replacement, uwuified_word)

        return uwuified_word


    def _add_space_element(
        self, word: str, next_word: str | None, index: int, sentence_seed: Seed,
    ) -> str:
        """Adds a face, action, or stutter after a word."""
        prob_face = self._spaces_modifier.get("faces", 0.0)
        prob_action = self._spaces_modifier.get("actions", 0.0)
        prob_stutter = self._spaces_modifier.get("stutters", 0.0)

        action_threshold = prob_face + prob_action
        stutter_threshold = action_threshold + prob_stutter

        is_last_word = next_word is None
        next_word_is_break = next_word is not None and self._is_break(next_word)
        can_add_space_element = not (
                self._is_break(word) or is_last_word or next_word_is_break
        )

        if not can_add_space_element:
            return word

        # Use a deterministic seed based on word position and sentence context
        word_space_seed = Seed(f"{word}_{index}_{sentence_seed.seed}")
        random_val = word_space_seed.random()

        result = word # Start with the original word

        if self.faces and 0.0 < random_val <= prob_face:
            face_idx = word_space_seed.random_int(0, len(self.faces) - 1)
            result += f" {self.faces[face_idx]}"
        elif self.actions and prob_face < random_val <= action_threshold:
            action_idx = word_space_seed.random_int(0, len(self.actions) - 1)
            result += f" {self.actions[action_idx]}"
        elif prob_stutter > 0 and action_threshold < random_val <= stutter_threshold:
            if not self._is_uri(word) and not self._is_break(word) and word:
                first_char = word[0]
                stutter_count = word_space_seed.random_int(1, 2)
                result = f"{first_char}-" * stutter_count + word

        return result


    def _uwuify_exclamation(self, word: str) -> str:
        """Replaces trailing exclamation/question marks based on probability."""
        if not self.exclamations or self._is_break(word):
             return word

        match = self._EXCLAMATION_PATTERN.search(word)
        if not match:
            return word

        excl_seed = Seed(word)
        if excl_seed.random() < self.exclamations_modifier:
            word_stem = word[:match.start()]
            excl_idx = excl_seed.random_int(0, len(self.exclamations) - 1)
            return word_stem + self.exclamations[excl_idx]
        return word

    # --- Public API Method ---
    def uwuify(self, text: str) -> str:
        """Apply all uwuification transformations to the input text.

        Args:
            text: The original text string.

        Returns:
            The fully uwuified text string,
            or an empty string if input fails conversion.
        """
        if not isinstance(text, str):
            logger.warning(
                f"Input was not a string ({type(text)}), attempting conversion.",
            )
            try:
                text = str(text)
            except Exception:
                logger.exception("Could not convert input to string.")
                return ""

        if not text.strip():
            return text

        words: list[str] = text.split(" ")
        sentence_seed = Seed(text)

        # 1. Apply word transformations
        transformed_words = [
            self._uwuify_word(word, sentence_seed.seed) for word in words
        ]

        # 2. Apply exclamation transformations
        exclamation_transformed_words = [
            self._uwuify_exclamation(word) for word in transformed_words
        ]

        # 3. Apply space transformations
        final_words: list[str] = []
        num_words = len(exclamation_transformed_words)
        for i, current_word in enumerate(exclamation_transformed_words):
            if not current_word: # Handle empty strings from multiple spaces
                # Preserve empty strings if they resulted from split(' ')
                final_words.append(current_word)
                continue

            next_word = (
                exclamation_transformed_words[i + 1]
                if i + 1 < num_words else None
            )
            processed_word = self._add_space_element(
                current_word, next_word, i, sentence_seed,
            )
            final_words.append(processed_word)

        result = " ".join(final_words)
        logger.info("Text uwuified successfully.")
        return result

    # Alias for backward compatibility or preference
    def uwuify_sentence(self, sentence: str) -> str:
         """Alias for the uwuify method."""
         return self.uwuify(sentence)

