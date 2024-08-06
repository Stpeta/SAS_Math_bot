from dataclasses import dataclass

from environs import Env


@dataclass
class TgBot:
    token: str  # Token for access to the telegram bot
    admin_ids: list[int]  # lists of administrators id
    anthropic_api_key: str  # api key for anthropic.ai
    max_dialogue_length: int
    ai_model: str
    max_tokens: int


@dataclass
class Config:
    tg_bot: TgBot


# A function that will read the .env file and return
# instance of the Config class with the token and admin_ids fields filled in
def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        tg_bot=TgBot(
            token=env('BOT_TOKEN'),
            admin_ids=list(map(int, env.list('ADMIN_IDS'))),
            anthropic_api_key=env('ANTHROPIC_API_KEY'),
            max_dialogue_length=20000,
            ai_model='claude-3-haiku-20240307',
            max_tokens=1000
        )
    )
