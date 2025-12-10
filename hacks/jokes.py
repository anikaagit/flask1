import random, json, os, fcntl
from flask import current_app

jokes_data = []
joke_list = [
    "How did you feel about the character choices and the naming conventions? "
    "Was the morning routine level too difficult?",
    "How did you feel about the extra challenge in the work maze, being unable to take the same path twice?",
    "How did you feel about the speed that whack-a-candy ran at?",
    "Was the dialogue in the dialogue level engaging enough to keep your interest?",
    "Was the interactablilty of the launch party level sufficient?",
    "Was the pacing of the game appropriate?",
    "Was the UI experience good?",
    "Would you play the game again?",
    "Would you recommend the game to a friend?",
    "Did you encounter any bugs or glitches?",

]

def get_jokes_file():
    # Always use Flask app.config['DATA_FOLDER'] for shared data
    data_folder = current_app.config['DATA_FOLDER']
    return os.path.join(data_folder, 'jokes.json')

def _read_jokes_file():
    JOKES_FILE = get_jokes_file()
    if not os.path.exists(JOKES_FILE):
        return []
    with open(JOKES_FILE, 'r') as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except Exception:
            data = []
        fcntl.flock(f, fcntl.LOCK_UN)
    return data

def _write_jokes_file(data):
    JOKES_FILE = get_jokes_file()
    with open(JOKES_FILE, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f)
        fcntl.flock(f, fcntl.LOCK_UN)

def initJokes():
    JOKES_FILE = get_jokes_file()
    # Only initialize if file does not exist
    if os.path.exists(JOKES_FILE):
        return
    jokes_data = []
    item_id = 0
    for item in joke_list:
        jokes_data.append({"id": item_id, "joke": item, "haha": 0, "boohoo": 0})
        item_id += 1
    # prime some haha responses
    for i in range(10):
        id = random.choice(jokes_data)['id']
        jokes_data[id]['haha'] += 1
    for i in range(5):
        id = random.choice(jokes_data)['id']
        jokes_data[id]['boohoo'] += 1
    _write_jokes_file(jokes_data)
        
def getJokes():
    return _read_jokes_file()

def getJoke(id):
    jokes = _read_jokes_file()
    return jokes[id]

def getRandomJoke():
    jokes = _read_jokes_file()
    return random.choice(jokes)

def favoriteJoke():
    jokes = _read_jokes_file()
    best = 0
    bestID = -1
    for joke in jokes:
        if joke['haha'] > best:
            best = joke['haha']
            bestID = joke['id']
    return jokes[bestID] if bestID != -1 else None
    
def jeeredJoke():
    jokes = _read_jokes_file()
    worst = 0
    worstID = -1
    for joke in jokes:
        if joke['boohoo'] > worst:
            worst = joke['boohoo']
            worstID = joke['id']
    return jokes[worstID] if worstID != -1 else None


# Atomic vote update with exclusive lock
def _vote_joke(id, field):
    JOKES_FILE = get_jokes_file()
    with open(JOKES_FILE, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        jokes = json.load(f)
        jokes[id][field] += 1
        # Move file pointer to start before writing updated JSON
        f.seek(0)
        json.dump(jokes, f)
        # Truncate file to remove any leftover data from previous content
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)
    return jokes[id][field]

def addJokeHaHa(id):
    return _vote_joke(id, 'haha')

def addJokeBooHoo(id):
    return _vote_joke(id, 'boohoo')

def printJoke(joke):
    print(joke['id'], joke['joke'], "\n", "haha:", joke['haha'], "\n", "boohoo:", joke['boohoo'], "\n")

def countJokes():
    jokes = _read_jokes_file()
    return len(jokes)

if __name__ == "__main__": 
    initJokes()  # initialize jokes
    
    # Most likes and most jeered
    best = favoriteJoke()
    if best:
        print("Most liked", best['haha'])
        printJoke(best)
    worst = jeeredJoke()
    if worst:
        print("Most jeered", worst['boohoo'])
        printJoke(worst)
    
    # Random joke
    print("Random joke")
    printJoke(getRandomJoke())
    
    # Count of Jokes
    print("Jokes Count: " + str(countJokes()))