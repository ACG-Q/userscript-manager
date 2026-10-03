from .base import BaseSourceAdapter, ScriptSource, get_adapter, get_all_adapters, register_adapter
from .direct_url import DirectUrlAdapter
from .github_gist import GitHubGistAdapter
from .greasyfork import GreasyForkAdapter
from .userscript_zone import UserscriptZoneAdapter

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