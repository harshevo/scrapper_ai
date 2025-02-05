from typing import Annotated
from pydantic_settings import BaseSettings

from pydantic.functional_validators import AfterValidator
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


def validate_api_key(api_key: str) -> str:
    if not api_key:
        raise ValueError("API key is required.")
    return api_key


ApiKey = Annotated[str, AfterValidator(validate_api_key)]


class Settings(BaseSettings):
    # OPENAI_API_KEY: str
    ANTHROPIC: str
    TAVILY: str
