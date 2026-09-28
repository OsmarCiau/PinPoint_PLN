import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Pinpoint PLN"
    debug: bool = False
    freeling_bin: str = "/opt/homebrew/bin/analyzer"
    freeling_share: str = "/opt/homebrew/share/freeling"
    freeling_config: str = "/opt/homebrew/share/freeling/config/es.cfg"
    supported_languages: list[str] = ["spa", "eng"]
    max_clues: int = 5
    show_relation_tags: bool = False

    def get_freeling_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["FREELINGSHARE"] = self.freeling_share
        return env

    def is_freeling_available(self) -> bool:
        return Path(self.freeling_bin).is_file() and Path(self.freeling_config).is_file()


settings = Settings()
