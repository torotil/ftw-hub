import copy
import itertools


def merge_dicts(*sources):
    """Create a new dict with all the source dictionaries recusively merged.

    Values on the right override values on the left. Lists are concatenated.
    """
    sources = list(sources)
    merged = {}
    while sources:
        source = sources.pop()
        for key in source:
            if key in merged:
                pass
            # Source is the rightmost value.
            # - Recursively merge dicts.
            elif isinstance(source[key], dict):
                key_sources = [s[key] for s in sources if key in s and isinstance(s[key], dict)]
                key_sources.append(source[key])
                merged[key] = merge_dicts(*key_sources)
            # - Concatenate lists.
            elif isinstance(source[key], list):
                key_sources = [s[key] for s in sources if key in s and isinstance(s[key], list)]
                key_sources.append(source[key])
                merged[key] = list(itertools.chain(*key_sources))
            # - Use the rightmost value for everything else.
            else:
                merged[key] = copy.deepcopy(source[key])
    return merged
