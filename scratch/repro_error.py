from providers.base import BaseProvider, ProviderConfig
from providers.nvidia_nim.client import NvidiaNimProvider
from config.nim import NimSettings

config = ProviderConfig(api_key="test")
nim_settings = NimSettings()

try:
    provider = NvidiaNimProvider(config, nim_settings=nim_settings)
    print("Successfully initialized provider")
    print(f"Config: {provider.config}")
except AttributeError as e:
    print(f"Caught expected error: {e}")
except Exception as e:
    print(f"Caught unexpected error: {type(e).__name__}: {e}")
