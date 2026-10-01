from .base import BaseSourceAdapter, ScriptSource, register_adapter, get_adapter, get_all_adapters
from .greasyfork import GreasyForkAdapter
from .userscript_zone import UserscriptZoneAdapter
from .github_gist import GitHubGistAdapter
from .direct_url import DirectUrlAdapter

# Register all adapters
register_adapter(GreasyForkAdapter())
register_adapter(UserscriptZoneAdapter())
register_adapter(GitHubGistAdapter())
register_adapter(DirectUrlAdapter())

__all__ = [
    "BaseSourceAdapter",
    "ScriptSource",
    "register_adapter",
    "get_adapter",
    "get_all_adapters",
    "GreasyForkAdapter",
    "UserscriptZoneAdapter",
    "GitHubGistAdapter",
    "DirectUrlAdapter",
]