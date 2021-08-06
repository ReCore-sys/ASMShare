from fuzzywuzzy import fuzz
from loguru import logger


@logger.catch
def search(search_dict: dict,
           query: str) -> dict:
    """
Fuzzy search nested dictionaries

     Parameters
     ----------
     search_dict : dict
     The dictionary to search

     query : str
     The words to match for


     Returns
     -------
     results : dict
     The ordered dict that is sorted by similarity to the query
    """

    # Create a dictionary to store
    scoretable = {k: 0 for k in search_dict}

    # Create empty dict to store the results in
    results = {}

    # Looping fun
    for y in search_dict:
        for x in search_dict[y]:
            if x not in ["score", "date", "image"]:
                if type(search_dict[y][x]) == list:
                    accuracy = 0
                    for value in search_dict[y][x]:
                        accuracy += fuzz.ratio(value.lower(), query.lower())
                else:
                    # This function from fuzzywuzzy works out the similarity of the 2 arguments in a score of 1-100
                    accuracy = fuzz.ratio((search_dict[y][x]).lower(), query.lower())

                # if the query is directly in the part we are matching for (ie, if we search for "example", if the
                # result for the section is "lorum ipsum example") add 50 points. This helps narrow searches when you
                # know exactly what you are after
                if type(search_dict[y][x]) == list:
                    for value in search_dict[y][x]:
                        if query.lower() in value.lower():
                            accuracy *= 2
                else:
                    if query.lower() in search_dict[y][x].lower():
                        accuracy *= 2

                # add the points the the scoretable, then start again
                scoretable[y] += round(accuracy)

    # Sort the dict by the values from biggest to smallest
    scoretable = {k: v for k, v in sorted(scoretable.items(), key=lambda item: item[1], reverse=True)}

    # Now some funky logic to narrow the search for a query
    # First we compile a list of all the scores
    vals = [scoretable[x] for x in scoretable]
    # Assign the biggest and smallest to mx and mn
    mx, mn = max(vals), min(vals)
    print("Min and max: ", mx, mn)
    # Get the range
    rng = mx - mn
    print("range", rng)
    # Set a percentage. This can be tweaked
    percentage = 75
    # Get a threshold based off these number (Gets percentage% of the range, then adds it to the min)
    threshold = mn + round((rng / 100) * percentage)
    print("threshold: ", threshold)
    print("")
    for x in scoretable:
        print(f"{x}: {scoretable[x]}")
        # Only include the item if it's score is over the threshold
        if scoretable[x] > threshold:
            results[x] = search_dict[x]

    # return it
    return results
