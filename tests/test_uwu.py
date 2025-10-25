import random
import string
from unittest.mock import ANY, Mock, patch

import pytest
from pytest_mock import MockerFixture

from packages.uwu import Uwuifier, UwuifierConfig

DEFAULT_CONFIG = {
    "words": 0.2,
    "spaces": {
        "faces": 0.08,
        "actions": 0.05,
        "stutters": 0.1,
    },
    "exclamations": 0.8,
}

ALWAYS_APPLY_WORD_CASES = [
    # I hate life
    ("running", "wunnying"),
    ("love", "wuv"),
    ("no", "nyo"),
    ("Hello", "Hewwo"),
    ("OVER", "uvw"),
    ("Really", "weawwy"),
    ("Lorry", "wowwy"),
    ("another", "anyothew"),
    ("never", "nyevew"),
]

INVALID_WORD_CASES = [
    "the",
    "a",
    "I",
    "you",
    "we",
    "they",
    "is",
    "was",
    "be",
]

NORMAL_WORD_CASES = [
    ("running", "wunnying"),
    ("love", "wove"),
    ("no", "nyo"),
    ("Hello", "Hewwo"),
    ("OVER", "OVEw"),
] # There'll be fewer cases as it is only to test the random chances.

INVALID_PUNC_CASES = [
    "never#",
    "gonna.",
    "gi!ve;",
    "yo?u,",
    "up%",
    "never^",
    "gonna&",
    "let*",
    "you(",
    "down)",
    "never_",
    "gonna-", # the lyric stops here
]

# Multiple same cases to check for randomness
# And it's deeply suspicious why it's always "!?".
# I guess that's what happens with seed 123.
NORMAL_PUNC_CASES = [
    ("let!", "let!?"), # SIKE, it continues :3
    ("you?", "you!?"),
    ("down!", "down!?"),
    ("never?", "never!?"),
    ("gonna!", "gonna!?"),
    ("run?", "run!?"),
]

CONFIG_FACE_ONLY = {
    "words": 0.0, # Disable word modifications
    "spaces": {
        "faces": 1.0,
        "actions": 0.0,
        "stutters": 0.0,
    },
    "exclamations": 0.0, # Disable exclamation modifications
}

CONFIG_ACTION_ONLY = {
    "words": 0.0,
    "spaces": {
        "faces": 0.0,
        "actions": 1.0,
        "stutters": 0.0,
    },
    "exclamations": 0.0,
}

CONFIG_STUTTER_ONLY = {
    "words": 0.0,
    "spaces": {
        "faces": 0.0,
        "actions": 0.0,
        "stutters": 1.0,
    },
    "exclamations": 0.0,
}

# Each input text generates a unique seed,
# forcing a specific output from the rng.choices().
# The expected outputs rely on the predefined lists (_FACES, _ACTIONS) and their order.
NORMAL_SPACE_CASES = [
    (
        CONFIG_FACE_ONLY,
        "Test sentence for face injection.",
        "Test sentence for face injection. ;;w;;",
    ),
    (
        CONFIG_ACTION_ONLY,
        "Test sentence for action injection.",
        "Test sentence for action injection. \\*cries\\*",
    ),
    (
        CONFIG_STUTTER_ONLY,
        "Test sentence for stutter injection.",
        "T-Test sentence for stutter injection.",
    ),
    (
        CONFIG_FACE_ONLY,
        "Test that nothing happens if the next word is punctuation.",
        "Test that nothing happens if the next word is punctuation. ;;w;;",
    ),
]

CHAR_POOL = string.ascii_letters + string.digits

def generate_word() -> str:
    """Generates a random alphanumeric string with a length between 2 and 5."""
    length = random.randint(2, 5)
    return "".join(random.choice(CHAR_POOL) for _ in range(length))

def generate_random_text(
    min_words: int = 10,
    max_words: int = 20,
    comma_chance: int = 0.15,
) -> str:
    """Generates a sentence of random text following the defined rules.

    Args:
        min_words (int): Minimum number of words in the sentence.
        max_words (int): Maximum number of words in the sentence.
        comma_chance (float): Probability (0.0 to 1.0)
                              of a comma appearing after a word.
    """
    # 1. Determine the sentence length
    num_words = random.randint(min_words, max_words)

    token_list = []

    # 2. Generate words and insert commas randomly
    for i in range(num_words):
        word = generate_word()
        token_list.append(word)

        # Insert a comma if random chance dictates it,
        # but avoid adding a comma right before the final word
        if i < num_words - 1 and random.random() < comma_chance:
            token_list.append(",")

    # 3. Format the text (Handle spaces correctly around punctuation)
    final_text = []
    for token in token_list:
        if token == ",":
            # If the token is a comma, append it directly to the previous word
            # (removing the space before the comma)
            if final_text:
                last_word = final_text.pop()
                final_text.append(last_word + token)
        else:
            final_text.append(token)

    # Join everything with spaces
    output = " ".join(final_text)

    # 4. Add the required period at the end
    output += "."

    return output


@pytest.fixture
def mocked_uwuifier(mocker: MockerFixture) -> dict:
    """Fixture that instantiates Uwuifier and patches its internal methods.

    Returns:
        A dictionary containing the instance and the mock objects.
    """
    uwu_instance = Uwuifier()

    mock_uwuify_word = mocker.patch.object(
        uwu_instance,
        "_uwuify_word",
        side_effect=lambda w, rng: w,
    )
    mock_uwuify_exclamation = mocker.patch.object(
        uwu_instance,
        "_uwuify_exclamation",
        side_effect=lambda w, rng: w,
    )
    mock_uwuify_add_space_element = mocker.patch.object(
        uwu_instance,
        "_add_space_element",
        side_effect=lambda w, rng: w,
    )

    return {
        "instance": uwu_instance,
        "word": mock_uwuify_word,
        "exclamation": mock_uwuify_exclamation,
        "space": mock_uwuify_add_space_element,
    }


@pytest.fixture
def default_config() -> dict:
    """The default config for the Uwuifier class."""
    return DEFAULT_CONFIG

@patch("packages.uwu.deepcopy", return_value=DEFAULT_CONFIG)
def test_uwuifier_init(mock_deepcopy: Mock, default_config: dict) -> None:
    """Test basic class initialization."""
    uwu_instance = Uwuifier()

    assert uwu_instance.words_modifier == default_config["words"]
    assert uwu_instance.spaces_modifier == default_config["spaces"]
    assert uwu_instance.exclamations_modifier == default_config["exclamations"]

    mock_deepcopy.assert_called_once_with(DEFAULT_CONFIG)

def test_uwuifier_config() -> None:
    """Test class initialization with custom config."""
    config: UwuifierConfig = {
        "words": 0.3,
        "spaces": {
            "faces": 0.1,
            "actions": 0.07,
            "stutters": 0.1,
        },
        "exclamations": 0.9,
    }

    uwu_instance = Uwuifier(config)
    assert uwu_instance.words_modifier == config["words"]
    assert uwu_instance.spaces_modifier == config["spaces"]
    assert uwu_instance.exclamations_modifier == config["exclamations"]

def test_uwuifier_invalid_config() -> None:
    """Test class initialization with invalid config."""
    config = {
        "words": 0.3,
        "spaces": "not a dict",
        "exclamations": 0.9,
    }

    with pytest.raises(TypeError) as exc_info:
        Uwuifier(config) # type: ignore

    assert str(
        exc_info.value,
    ) == "The 'spaces' key in the configuration must be a dictionary, but got type str."

def test_is_word_skippable() -> None:
    """Test the is_word_skippable method."""
    uwu_instance = Uwuifier()
    assert uwu_instance._is_word_skippable("@IDontKnowWhyThe@SymbolIsSkippedButOk")
    assert uwu_instance._is_word_skippable(
        "https://youtube.com/watch?v=dQw4w9WgXcQ", # Not sorry
    )
    assert not uwu_instance._is_word_skippable("Normal")

@pytest.mark.parametrize(("input_word", "expected_output"), NORMAL_WORD_CASES)
def test_uwuify_word(input_word: str, expected_output: str) -> None:
    """Test if the _uwuify_word method always uwuifies a word if words == 1."""
    uwu_instance = Uwuifier()
    random_instance = random.Random(123) # doesn't matter
    assert uwu_instance._uwuify_word(input_word, random_instance) == expected_output

@pytest.mark.parametrize(("input_word", "expected_output"), ALWAYS_APPLY_WORD_CASES)
def test_uwuify_word_always(input_word: str, expected_output: str) -> None:
    """Test if the _uwuify_word method always uwuifies a word if words == 1."""
    config: UwuifierConfig = {
        "words": 1.0,
    }
    uwu_instance = Uwuifier(config=config)
    random_instance = random.Random(123) # doesn't matter
    assert uwu_instance._uwuify_word(input_word, random_instance) == expected_output

def test_uwuify_word_never() -> None:
    """Test if the _uwuify_word method doesn't uwuifies a word if words == 0."""
    texts = [text for text in random.choice(string.ascii_letters) for _ in range(30)]

    config: UwuifierConfig = {
        "words": 0.0,
    }

    for text in texts:
        uwu_instance = Uwuifier(config=config)
        random_instance = random.Random(123)

        assert uwu_instance._uwuify_word(text, random_instance) == text

@pytest.mark.parametrize("word", INVALID_WORD_CASES)
def test_uwuify_word_invalid(word: str) -> None:
    """Test if the _uwuify_word method doesn't uwuifies a word that it shouldn't."""
    config: UwuifierConfig = {
        "words": 0.0,
    }

    uwu_instance = Uwuifier(config=config)
    random_instance = random.Random(123)

    assert uwu_instance._uwuify_word(word, random_instance) == word

@pytest.mark.parametrize(("input_word", "expected_output"), NORMAL_PUNC_CASES)
def test_uwuify_exclamation(
    input_word: str,
    expected_output: str,
) -> None:
    """Test normal conditions for _uwuify_exclamation."""
    uwu_instance = Uwuifier()
    random_instance = random.Random(123)

    assert uwu_instance._uwuify_exclamation(
        input_word, random_instance,
    ) == expected_output

@pytest.mark.parametrize("word", INVALID_PUNC_CASES)
def test_uwuify_exclamation_invalid_punctuation(
    word: str,
) -> None:
    """Test if _uwuify_exclamation doesn't apply that it shouldn't."""
    config: UwuifierConfig = {
        "words": 0.0,
    }

    uwu_instance = Uwuifier(config=config)
    random_instance = random.Random(123)

    assert uwu_instance._uwuify_exclamation(
        word, random_instance,
    ) == word

@pytest.mark.parametrize(("input_word", "expected_output"), NORMAL_PUNC_CASES)
def test_uwuify_exclamation_never(
    input_word: str,
    expected_output: str,
) -> None:
    """Test if _uwuify_exclamation doesn't apply if exclamations == 0."""
    config: UwuifierConfig = {
        "exclamations": 0.0,
    }

    uwu_instance = Uwuifier(config=config)
    random_instance = random.Random(123)

    assert uwu_instance._uwuify_exclamation(
        input_word, random_instance,
    ) == input_word

@pytest.mark.parametrize(("input_word", "expected_output"), NORMAL_PUNC_CASES)
def test_uwuify_exclamation_always(
    input_word: str,
    expected_output: str,
) -> None:
    """Test if _uwuify_exclamation always applies if exclamations == 1."""
    config: UwuifierConfig = {
        "exclamations": 1.0,
    }

    uwu_instance = Uwuifier(config=config)
    random_instance = random.Random(123)

    assert (
        uwu_instance._uwuify_exclamation(
            input_word,
            random_instance,
        )
        != input_word
    )  # it's cheating I know, but it works

@pytest.mark.parametrize(
    ("config", "input_text", "expected_output"),
    NORMAL_SPACE_CASES,
)
def test_add_space_element(
    config: UwuifierConfig,
    input_text: str,
    expected_output: str,
) -> None:
    """Test the insertion of faces, actions, and stutters based on space modifiers."""
    uwu_instance = Uwuifier(config=config)
    random_instance = random.Random(123)
    result = uwu_instance._add_space_element(input_text, random_instance)

    assert result == expected_output

def test_add_space_element_never() -> None:
    """Test if the insertion of faces, actions, and stutters doesn't happen.

    If all spaces == zero, it shouldn't happen.
    """
    config: UwuifierConfig = {
        "spaces": {
            "faces": 0.0,
            "actions": 0.0,
            "stutters": 0.0,
        },
    }

    uwu_instance = Uwuifier(config=config)
    random_instance = random.Random(123)

    random_texts = [generate_random_text() for _ in range(100)]
    for text in random_texts:
        assert uwu_instance._add_space_element(text, random_instance) == text

def test_uwuify() -> None:
    """Test the default uwuify behavior."""
    uwu_instance = Uwuifier()
    uwuified_text = uwu_instance.uwuify("The quick brown fox jumps over the lazy dog.")

    assert (
        uwuified_text
        == r"The quick b-b-brown fox ^-^ jumps over \*screams\* the lazy dog."
    )


def test_uwuify_function_calls(mocked_uwuifier: dict) -> None:
    """Test if the correct function is called inside the uwuify method."""
    input_text = "This is a test sentence."

    # Expected words (split by space):
    expected_words = ["This", "is", "a", "test", "sentence."]

    uwuifier_instance = mocked_uwuifier["instance"]
    mock_uwuify_word = mocked_uwuifier["word"]
    mock_uwuify_exclamation = mocked_uwuifier["exclamation"]
    mock_uwuify_add_space_element = mocked_uwuifier["space"]

    uwuifier_instance.uwuify(input_text)

    all_calls_word = mock_uwuify_word.call_args_list
    all_calls_exclamation = mock_uwuify_exclamation.call_args_list
    all_calls_add_space_element = mock_uwuify_add_space_element.call_args_list

    rng_objects_passed = []

    def collect_rng_objects(call_list: list) -> None:
        for call in call_list:
            # The RNG object is the second positional argument (index 1)
            rng_arg = call[0][1]
            rng_objects_passed.append(rng_arg)
            assert isinstance(rng_arg, random.Random), (
                f"Expected type random.Random, but got {type(rng_arg).__name__}"
            )

    collect_rng_objects(all_calls_word)
    collect_rng_objects(all_calls_exclamation)
    collect_rng_objects(all_calls_add_space_element)

    assert mock_uwuify_word.call_count == len(expected_words)
    assert mock_uwuify_exclamation.call_count == len(expected_words)
    assert mock_uwuify_add_space_element.call_count == len(expected_words) - 1

    for i, word in enumerate(expected_words):
        mock_uwuify_word.assert_any_call(word, ANY)
        mock_uwuify_exclamation.assert_any_call(word, ANY)

        # Excluding the last one
        if i + 1 < len(expected_words):
            mock_uwuify_add_space_element.assert_any_call(word, ANY)

    # Ensure every element in the list is the same object as the first one
    if len(rng_objects_passed) > 1:
        first_rng = rng_objects_passed[0]
        assert all(rng is first_rng for rng in rng_objects_passed)


def test_uwuify_not_string() -> None:
    """Test if the uwuify method raises an exception if not a string."""
    with pytest.raises(TypeError) as exc_info:
        Uwuifier().uwuify(42)

    assert str(exc_info.value) == "text is not string!"

def test_uwuify_only_whitespaces(mocked_uwuifier: dict) -> None:
    """Test if the uwuify method ignores only whitespaces."""
    uwuifier_instance = mocked_uwuifier["instance"]
    mock_uwuify_word = mocked_uwuifier["word"]
    mock_uwuify_exclamation = mocked_uwuifier["exclamation"]
    mock_uwuify_add_space_element = mocked_uwuifier["space"]

    uwuifier_instance.uwuify("           ")

    assert (
        mock_uwuify_word.call_count
        == mock_uwuify_add_space_element.call_count
        == mock_uwuify_exclamation.call_count == 0
    )

def test_uwuify_ignore_whitespaces(mocked_uwuifier: dict) -> None:
    """Test if the uwuify method doesn't process whitespaces."""
    uwuifier_instance = mocked_uwuifier["instance"]
    mock_uwuify_word = mocked_uwuifier["word"]
    mock_uwuify_exclamation = mocked_uwuifier["exclamation"]
    mock_uwuify_add_space_element = mocked_uwuifier["space"]

    uwuifier_instance.uwuify("     a     ")

    assert (
        mock_uwuify_word.call_count
        == mock_uwuify_add_space_element.call_count
        == mock_uwuify_exclamation.call_count == 1
    )

def test_uwuify_skippable(mocked_uwuifier: dict) -> None:
    """Test if the uwuify method doesn't process text that need to be skipped."""
    uwuifier_instance = mocked_uwuifier["instance"]
    mock_uwuify_word = mocked_uwuifier["word"]
    mock_uwuify_exclamation = mocked_uwuifier["exclamation"]
    mock_uwuify_add_space_element = mocked_uwuifier["space"]

    uwuifier_instance.uwuify("@user https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert (
        mock_uwuify_word.call_count
        == mock_uwuify_add_space_element.call_count
        == mock_uwuify_exclamation.call_count == 0
    )

def test_uwuify_sentence_alias(mocker: MockerFixture) -> None:
    """Test if uwuify_sentence alias method works."""
    uwu_instance = Uwuifier()
    mock_uwuify = mocker.patch.object(
        uwu_instance,
        "uwuify",
        side_effect=lambda sentence: sentence, # Returns itself
    )
    uwu_instance.uwuify_sentence("asdf")

    assert mock_uwuify.call_count == 1
