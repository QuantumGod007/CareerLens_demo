from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-2.5-flash'
    greenhouse_boards: str = 'stripe,cloudflare'
    lever_boards: str = 'spotify'
    data_dir: Path = ROOT / 'data'

    def prepare(self):
        self.data_dir = self.data_dir.resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.chmod(0o700)
        for folder in ('uploads', 'resumes'):
            (self.data_dir / folder).mkdir(parents=True, exist_ok=True)
            (self.data_dir / folder).chmod(0o700)
        return self


@lru_cache
def get_settings():
    return Settings().prepare()
