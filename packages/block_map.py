from google.genai.types import HarmBlockThreshold, HarmProbability

BLOCKED_SETTINGS = {
    "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    'BLOCK_MEDIUM_AND_ABOVE': HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    'BLOCK_ONLY_HIGH': HarmBlockThreshold.BLOCK_ONLY_HIGH,
    'BLOCK_NONE': HarmBlockThreshold.BLOCK_NONE
}

BLOCKED_CATEGORY = {
    'BLOCK_LOW_AND_ABOVE': [HarmProbability.LOW, HarmProbability.MEDIUM, HarmProbability.HIGH],
    'BLOCK_MEDIUM_AND_ABOVE': [HarmProbability.MEDIUM, HarmProbability.HIGH],
    'BLOCK_ONLY_HIGH': [HarmProbability.HIGH],
    'BLOCK_NONE': [HarmProbability.HIGH]
}

HARM_PRETTY_NAME = {
    'HARM_CATEGORY_SEXUALLY_EXPLICIT': "Sexually Explicit",
    'HARM_CATEGORY_HATE_SPEECH': 'Hate Speech',
    'HARM_CATEGORY_HARASSMENT': 'Harassment',
    'HARM_CATEGORY_DANGEROUS_CONTENT': 'Dangerous Content',
    'HARM_CATEGORY_CIVIC_INTEGRITY': 'Civil Integrity'
}