from app.core.settings import Settings
from app.modules.conversations.application import AnswerGenerator
from app.platform.ai.generation import DeterministicAnswerGenerator, OllamaAnswerGenerator


def create_answer_generator(settings: Settings) -> AnswerGenerator:
    if settings.answer_provider == "ollama":
        return OllamaAnswerGenerator(
            base_url=settings.ollama_base_url,
            model=settings.answer_model,
            timeout_seconds=settings.request_timeout_seconds,
            max_output_tokens=settings.answer_max_output_tokens,
        )
    return DeterministicAnswerGenerator()
