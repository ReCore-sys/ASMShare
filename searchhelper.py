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
                        accuracy += (fuzz.ratio(value.lower(), query.lower()) / len(search_dict[y][x]))
                else:
                    # This function from fuzzywuzzy works out the similarity of the 2 arguments in a score of 1-100
                    accuracy = fuzz.ratio((search_dict[y][x]).lower(), query.lower())

                # if the match is in the tags, double the score
                if x == "tags":
                    accuracy *= 2

                # if the query is directly in the part we are matching for (ie, if we search for "example", if the
                # result for the section is "lorum ipsum example") add 50 points. This helps narrow searches when you
                # know exactly what you are after
                if type(search_dict[y][x]) == list:
                    for value in search_dict[y][x]:
                        if query.lower() in value.lower():
                            accuracy += 50
                else:
                    if query.lower() in search_dict[y][x].lower():
                        accuracy += 50

                # add the points the the scoretable, then start again
                scoretable[y] += round(accuracy)

    # Sort the dict by the values from biggest to smallest
    scoretable = {k: v for k, v in sorted(scoretable.items(), key=lambda item: item[1], reverse=True)}

    # Now we sort our original dict so it has the same order as the scoreboard
    for x in scoretable:
        results[x] = search_dict[x]

    # return it
    return results
