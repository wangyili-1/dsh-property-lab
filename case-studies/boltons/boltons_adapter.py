"""Independent oracle for boltons.iterutils.unique on lists of integers."""


def reference_unique(values):
    """Keep each integer's first occurrence using equality and an explicit loop.

    Deliberately use no boltons call, set, dict, or unique_iter implementation.
    Integer equality and hash equality agree throughout the declared domain.
    """
    result = []
    for value in values:
        already_seen = False
        for previous in result:
            if previous == value:
                already_seen = True
                break
        if not already_seen:
            result.append(value)
    return result
