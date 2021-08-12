import json
import sqlite3
from fuzzywuzzy import fuzz
import time
import threading
thr = False


def search(search_dict: dict,
           query: str, thr) -> dict:
    """search \nReturns an ordered dict that is sorted by similarity to the given query

    Parameters
    ----------
    search_dict : dict
        List if all items to match for
    query : str
        The string to match against

    Returns
    -------
    dict
        A sorted dict that is ordered by it's relation to the query
    """
    # Only run in threaded mode for 300+ entries
    # Also only use this if not already set
    if "thr" not in locals():
        thr = len(search_dict) > 300
    modifiers = {
        "name": 2,
        "short": 1.2,
        "long": 0.9,
        "uploader": 1.6,
        "subject": 1.4,
        "tags": 1.75,
        "date": 0,
        "score": 0.5,
        "image": 0,
        "veryshort": 0.8
    }
    # Create a dictionary to store
    scoretable = {k: 0 for k in search_dict}

    # Create empty dict to store the results in
    results = {}

    def loop(y):
        for x in search_dict[y]:
            if type(search_dict[y][x]) == list:
                accuracy = 0
                for value in search_dict[y][x]:
                    accuracy += fuzz.ratio(value.lower(),
                                           query.lower()) * modifiers[x]
            else:
                # This function from fuzzywuzzy works out the similarity of the 2 arguments in a score of 1-100
                accuracy = fuzz.ratio(
                    str(search_dict[y][x]).lower(), str(query).lower()) * modifiers[x]

            # if the query is directly in the part we are matching for (ie, if we search for "example", if the
            # result for the section is "lorum ipsum example") add 50 points. This helps narrow searches when you
            # know exactly what you are after
            if type(search_dict[y][x]) == list:
                for value in search_dict[y][x]:
                    if query.lower() in value.lower():
                        accuracy *= 2
            else:
                if query.lower() in str(search_dict[y][x]).lower():
                    accuracy *= 2

            # add the points the the scoretable, then start again
            scoretable[y] += round(accuracy)
    if thr == False:
        # Looping fun
        for y in search_dict:
            loop(y)
    else:

        for y in search_dict:
            threading.Thread(target=loop, args=(y,))

    # Sort the dict by the values from biggest to smallest
    scoretable = {k: v for k, v in sorted(
        scoretable.items(), key=lambda item: item[1], reverse=True)}

    # Now some funky logic to narrow the search for a query
    # First we compile a list of all the scores
    vals = [scoretable[x] for x in scoretable]
    # Assign the biggest and smallest to mx and mn
    mx, mn = max(vals), min(vals)
    # Get the range
    rng = mx - mn
    # Set a percentage. This can be tweaked
    percentage = 75
    # Get a threshold based off these number (Gets percentage% of the range, then adds it to the min)
    threshold = mn + round((rng / 100) * percentage)
    for x in scoretable:
        # Only include the item if it's score is over the threshold
        if scoretable[x] >= threshold:
            results[x] = search_dict[x]

    # return it
    return results


if __name__ == '__main__':
    """compileimages\n
    Recompile the image dict
    """

    cards = {}
    db = sqlite3.connect("database.db")
    cursor = db.cursor()
    cursor.execute('SELECT * from test')
    # loops through all the entries in the db then adds the specified type to the dict
    for x in cursor.fetchall():
        # creates the dict entry for the file
        cards[x[9]] = {}
        # Data structure is fun (No it's not please help me)
        cards[x[9]]["name"] = x[0]
        # adds the short description
        cards[x[9]]["short"] = x[1]
        # adds the long description
        cards[x[9]]["long"] = x[2]
        # adds uploader's name
        cards[x[9]]["uploader"] = "test"
        # subject is added
        cards[x[9]]["subject"] = x[4]
        # tags
        if x[5] == None:
            cards[x[9]]["tags"] = "None"
        else:
            cards[x[9]]["tags"] = x[5].split(",")
        cards[x[9]]["date"] = x[6]
        cards[x[9]]["score"] = x[7]
        # uses the above function to get/create an image for the thumbnail
        cards[x[9]]["image"] = "test"
        # Shorter short description
        cards[x[9]]["veryshort"] = x[8]
    db.close()
    times = []
    timescount = []
    nontimes = []
    nontimescount = []
    nontimesavg = []
    timesavg = []
    print("Number of entries:", len(cards))
    for x in range(len(cards)):
        try:
            for y in range(10):

                start = time.time()
                res = search({k: cards[k]
                              for k in list(cards)[:x]}, "test", True)
                end = time.time()
                times.append((end-start)*1000)

            timesavg.append(sum(times)/len(times))
            timescount.append(x)
            times = []
        except:
            pass

    for x in range(len(cards)):
        try:
            for y in range(10):

                start = time.time()
                res = search({k: cards[k]
                              for k in list(cards)[:x]}, "test", False)
                end = time.time()
                nontimes.append((end-start)*1000)

            nontimescount.append(x)
            nontimesavg.append(sum(nontimes)/len(nontimes))
            nontimes = []
        except:
            pass

    with open("results.json") as j:
        j = json.load(j)
        j["timesavg"] = timesavg
        j["timescount"] = timescount
        j["nontimesavg"] = nontimesavg
        j["nontimescount"] = nontimescount
        json.dump(j, open("results.json", "w"))
