from app.providers.base import GeneratedImage, PollResult, Provider, ProviderError
from app.providers.fal import Fal
from app.providers.runpod import RunPodPublic, RunPodServerless

PROVIDERS: dict[str, Provider] = {p.name: p for p in (RunPodServerless(), RunPodPublic(), Fal())}

__all__ = ["PROVIDERS", "GeneratedImage", "PollResult", "Provider", "ProviderError"]
