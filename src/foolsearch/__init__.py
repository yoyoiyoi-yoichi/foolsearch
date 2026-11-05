"""FoolSearch: a foolproof keyword search engine.

Few keywords are enough, small typos are forgiven, and every hit says why
it matched. Standard library only.
"""
from .engine import Document, Match, SearchEngine, SearchResult

__all__ = ["Document", "Match", "SearchEngine", "SearchResult"]
__version__ = "0.1.0"
