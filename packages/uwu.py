import logging
import re
import random

MAX_UINT32 = 0xffffffff


class Seed:
    def __init__(self, seed):
        self.seed = hash(seed) & MAX_UINT32
        self.rng = random.Random(self.seed)  # Use Python's random module

    def random(self):
        return self.rng.random()

    def random_int(self, min_val, max_val):
        return self.rng.randint(min_val, max_val)


def is_at(word):
    return word.startswith("@")


def is_uri(word):
    return re.match(r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", word) is not None


def is_break(word):
    return word in [".", ",", "!", "?", ";"]


def get_capital_percentage(word):
    upper_count = sum(1 for char in word if char.isupper())
    return upper_count / len(word) if len(word) > 0 else 0


class Uwuifier:
    DEFAULTS = {
        "WORDS": 0.2,
        "SPACES": {"faces": 0.175 * 4/5, "actions": 0.15, "stutters": 0.15 * 4/5},
        "EXCLAMATIONS": 0.8,
    }

    def __init__(self, config=None):
        if config is None:
            config = {}
        words = config.get("words", self.DEFAULTS["WORDS"])
        spaces = config.get("spaces", self.DEFAULTS["SPACES"])
        exclamations = config.get("exclamations", self.DEFAULTS["EXCLAMATIONS"])

        self.faces = [
            "(・`ω´・)",
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
        self.exclamations = ["!?", "?!!", "?!?1", "!!11", "?!?!", "1!!1!"]
        self.actions = [
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
            r'\*drops armful of books\*'
        ]  # Thanks bartoneye for some of the actions!
        self.uwu_map = [
            [re.compile(r"[rl]", re.IGNORECASE), "w"],
            [re.compile(r"n([aeiou])", re.IGNORECASE), r"ny\1"],
            [re.compile(r"ove", re.IGNORECASE), "uv"],
        ]
        self._words_modifier = self.DEFAULTS["WORDS"]
        self._spaces_modifier = self.DEFAULTS["SPACES"]
        self._exclamations_modifier = self.DEFAULTS["EXCLAMATIONS"]
        self.words_modifier = words
        self.spaces_modifier = spaces
        self.exclamations_modifier = exclamations

    @property
    def words_modifier(self):
        return self._words_modifier

    @words_modifier.setter
    def words_modifier(self, value):
        if not 0 <= value <= 1:
            raise ValueError("wordsModifier value must be a number between 0 and 1")
        self._words_modifier = value

    @property
    def spaces_modifier(self):
        return self._spaces_modifier

    @spaces_modifier.setter
    def spaces_modifier(self, value):
        sum_val = sum(value.values())
        if not 0 <= sum_val <= 1:
            raise ValueError("spacesModifier value must be a number between 0 and 1")
        self._spaces_modifier = value

    @property
    def exclamations_modifier(self):
        return self._exclamations_modifier

    @exclamations_modifier.setter
    def exclamations_modifier(self, value):
        if not 0 <= value <= 1:
            raise ValueError("exclamationsModifier value must be a number between 0 and 1")
        self._exclamations_modifier = value

    def uwuify_words(self, sentence):
        """Applies word-level transformations based on regex."""
        words = sentence.split(" ")
        uwuified_sentence = []
        for word in words:
            if is_at(word) or is_uri(word):
                uwuified_sentence.append(word)
                continue
            seed = Seed(word)
            for old_word_regex, new_word in self.uwu_map:
                if seed.random() > self._words_modifier:
                    continue
                word = old_word_regex.sub(new_word, word)
            uwuified_sentence.append(word)
        return " ".join(uwuified_sentence)

    def uwuify_spaces(self, sentence):
        """Adds faces, actions, or stutters to spaces in the sentence."""
        words = sentence.split(" ")
        face_threshold = self._spaces_modifier["faces"]
        action_threshold = self._spaces_modifier["actions"] + face_threshold
        stutter_threshold = self._spaces_modifier["stutters"] + action_threshold
        uwuified_sentence = []

        for index, word in enumerate(words):
            seed = Seed(word)
            random_number = seed.random()
            first_character = word[0] if word else ""

            if (
                    self.faces
                    and random_number <= face_threshold
                    and not is_break(word)
            ):
                word += " " + self.faces[seed.random_int(0, len(self.faces) - 1)]
                self._check_capitalization(words, word, index, first_character)

            elif (
                    self.actions
                    and random_number <= action_threshold
                    and not is_break(word)
            ):
                word += " " + self.actions[seed.random_int(0, len(self.actions) - 1)]
                self._check_capitalization(words, word, index, first_character)

            elif (
                    random_number <= stutter_threshold
                    and not is_uri(word)
                    and not is_break(word)
                    and word
            ):
                stutter = seed.random_int(0, 2)
                word = (first_character + "-") * stutter + word

            uwuified_sentence.append(word)
        return " ".join(uwuified_sentence)

    @staticmethod
    def _check_capitalization(words, word, index, first_character):
        if first_character != first_character.upper():
            return
        if get_capital_percentage(word) > 0.5:
            return
        if index == 0:
            word = first_character.lower() + word[1:]
        else:
            previous_word = words[index - 1]
            previous_word_last_char = previous_word[-1] if previous_word else ""
            prev_word_ends_with_punctuation = re.search(r"[.!?\\-]", previous_word_last_char)
            if not prev_word_ends_with_punctuation:
                return
            word = first_character.lower() + word[1:]

    def uwuify_exclamations(self, sentence):
        """Transforms exclamation points with random variations."""
        words = sentence.split(" ")
        pattern = re.compile(r"[?!]+$")
        uwuified_sentence = []
        for word in words:
            seed = Seed(word)
            match = pattern.search(word)
            if (
                    not match
                    or seed.random() > self._exclamations_modifier
                    or is_break(word)
            ):
                uwuified_sentence.append(word)
                continue
            word = pattern.sub("", word)
            word += self.exclamations[seed.random_int(0, len(self.exclamations) - 1)]
            uwuified_sentence.append(word)
        return " ".join(uwuified_sentence)

    def uwuify_sentence(self, sentence):
        """Applies all uwuification transforms to a given sentence."""
        uwuified_string = sentence
        uwuified_string = self.uwuify_words(uwuified_string)
        logging.info("Uwuified words.")
        uwuified_string = self.uwuify_exclamations(uwuified_string)
        logging.info("Uwuified exclamations.")
        uwuified_string = self.uwuify_spaces(uwuified_string)
        logging.info("Uwuified string.")
        return uwuified_string