import twitter
import argparse
from os import getenv
from os.path import expanduser
from sys import exit
import json
import random
from twitter.api import TwitterHTTPError

def get_twitter():
    CONSUMER_KEY = getenv("CONSUMER_KEY")
    CONSUMER_SECRET = getenv("CONSUMER_SECRET")
    ACCESS_TOKEN = getenv("ACCESS_TOKEN")
    ACCESS_TOKEN_SECRET = getenv("ACCESS_TOKEN_SECRET")

    if not all((CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)):
        raise Exception("Please set the CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN and ACCESS_TOKEN_SECRET environment variables")

    return twitter.Twitter(
            auth=twitter.OAuth(ACCESS_TOKEN, ACCESS_TOKEN_SECRET,
                CONSUMER_KEY, CONSUMER_SECRET))

def save_state(state, filename):
    with open(filename, 'w') as f:
        json.dump(state, f, indent=2)

def sample_pop(population, k):
    """its like random.sample but it also pops ok"""
    out = list()
    for i in sorted(random.sample(range(len(population)), k), reverse=True):
        out.append(population.pop(i))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deletes old tweets past a specified number of tweets")
    parser.add_argument("--state-file", "-s", default=expanduser("~/.limiter.state"))

    commands = parser.add_subparsers(title="Commands", dest="command")


    update = commands.add_parser("update")

    prune = commands.add_parser("prune")
    prune.add_argument("--target", "-t", type=int, help="Target number of tweets", default=666)
    prune.add_argument("--max", "-m", type=int, help="Maximum number of tweets to delete")
    prune.add_argument("--no-keep-favs", action='store_true', help="Unless specified, tweets that have been favourited by yourself will be spared")
    prune.add_argument("--dry-run", "-n", action='store_true')

    commands.add_parser("check")

    args = parser.parse_args()

    try:
        tw = get_twitter()
        me = tw.account.verify_credentials()
    except Exception as e:
        print(e)
        exit(1)

    try:
        with open(args.state_file) as f:
            state = json.load(f)

            if "version" not in state:
                state["tweets_skipped"] = []
                state["version"] = 1

            state["tweets"] += state["tweets_skipped"]
            state["tweets_skipped"] = []

    except IOError:
        print("Couldn't open state file, starting from scratch")
        state = {
                "tweets": [],
                "archived": [],
                "tweets_skipped": [],
                "version": 1
                }
    except Exception as e:
        print("Couldn't load state file, possibly corrupted? %s", (e,))
        exit(1)

    if args.command == "update":
        print("Fetching new tweets for %s (@%s)" % (me['name'], me['screen_name']))

        kwargs = { 'user_id': me['id'], 'count': 200, 'trim_user': True }
        if len(state["tweets"]) > 0:
            kwargs['since_id'] = max((tweet["id"] for tweet in state["tweets"]))

        fetched = 0

        while True:
            tweets = tw.statuses.user_timeline(**kwargs)

            for tweet in tweets:
                state["tweets"].append(tweet)
                if 'max_id' not in kwargs or tweet['id'] < kwargs['max_id']:
                    kwargs['max_id'] = tweet['id'] - 1
                print(tweet['id'], tweet['text'])

            if len(tweets) == 0:
                break

            fetched += len(tweets)
            print("%s new tweets" % (fetched,))

            try:
                save_state(state, args.state_file)
            except Exception as e:
                print("Couldn't save state: %s" % (e,))
                exit(1)

        print("%s tweets in total" % (len(state['tweets']),))



    elif args.command == "check":
        for tweet in state["tweets"]:
            if not isinstance(tweet, dict) or\
            "id" not in tweet or "text" not in tweet:
                print("Invalid tweet: %s" % (tweet))

    elif args.command == "prune":
        delete_count = max(me['statuses_count'] - args.target, 0)

        if args.max and args.max < delete_count:
            delete_count = args.max

        if delete_count != 0:
            print("About to delete %s tweets..." % (delete_count,))

        while delete_count > 0:
            if len(state["tweets"]) == 0:
                print("Ran out of tweets! Giving up... (Maybe run an update first?)")
                exit(0)

            sample = sample_pop(state["tweets"],
                    min(100, len(state["tweets"])))
            sample = tw.statuses.lookup(trim_user=True,
                    _id=",".join((tweet["id_str"] for tweet in sample)))
            for tweet in sample:
                if delete_count <= 0 or \
                (tweet['favorited'] and not args.no_keep_favs):
                    state["tweets_skipped"].append(tweet)
                elif args.dry_run:
                    print(tweet['id'], tweet['text'])
                    print(". would have been deleted")
                    state["tweets_skipped"].append(tweet)
                    delete_count -= 1
                else:
                    try:
                        tw.statuses.destroy(id=tweet['id'])
                        print(tweet['id'], tweet['text'])
                        print("X is now deleted")
                        state["archived"].append(tweet)
                        delete_count -= 1
                    except TwitterHTTPError as e:
                        if(e.e.code == 404):
                            print("? was already gone")
                        else:
                            #???
                            raise

            try:
                save_state(state, args.state_file)
            except Exception as e:
                print("Couldn't save state: %s" % (e,))
                exit(1)

        state["archived"] = state["archived"][-100:]
        state["tweets"] += state["tweets_skipped"]
        state["tweets_skipped"] = list()

        try:
            save_state(state, args.state_file)
        except Exception as e:
            print("Couldn't save state: %s" % (e,))
            exit(1)
