from enum import StrEnum


class FeedbackReason(StrEnum):
    HELPFUL = "helpful"
    INCORRECT = "incorrect"
    UNSUPPORTED = "unsupported"
    CITATION_MISMATCH = "citation_mismatch"
    INCOMPLETE = "incomplete"
    UNCLEAR_LANGUAGE = "unclear_language"
    SHOULD_HAVE_ABSTAINED = "should_have_abstained"
