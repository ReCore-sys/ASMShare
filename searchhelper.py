from fuzzywuzzy import fuzz


def search(all, query):

    # Create a dictionary to store
    scoretable = {v: 0 for v in all}

    # Create empty dict to store the results in
    results = {}

    # Looping fun
    for y in all:
        for x in all[y]:

            # This function from fuzzywuzzy works out the similarity of the 2 arguments in a score of 1-100
            acc = fuzz.ratio(all[y][x].lower(), query.lower())

            # if the match is in the tags, double the score
            if y == "tags":
                acc *= 2

            # if the query is directly in the part we are matching for (ie, if we search for "example", if the result for the section is "lorum ipsum example") add 50 points. This helps narrow searches when you know exactly what you are after
            if query.lower() in all[y][x].lower():
                acc += 50

            # add the points the the scorboard, then start again
            scoretable[y] += acc

    # Sort the dict by the values from biggest to smallest
    scoretable = {k: v for k, v in sorted(scoretable.items(), key=lambda item: item[1], reverse=True)}

    # Now we sort our original dict so it has the same order as the scorboard
    for x in scoretable:
        print(f"{x}: {scoretable[x]}")
        results[x] = all[x]

    # return it
    return results
