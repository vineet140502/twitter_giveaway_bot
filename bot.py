import tweepy
import time
import pandas as pd
import os


current_dir = os.getcwd()
last_seen_file = "/last_seen.txt"
keys_file = "/keys.txt"
query_id_file = "/query_id.txt"
query_data_file = "/query_data.csv"
tweet_data_file = "/tweet_data.csv"

def get_info():
    info={}
    with open(current_dir+keys_file,"r") as f:
        for line in f.read().split("\n"):
            info[line.split("=")[0]]=line.split("=")[1]
        return info

def read_file(filename):
    with open(current_dir+filename,"r") as f:
        return int(f.read().strip())

def save_to_file(filename,data):
    with open(current_dir+filename,"w") as f:
        f.write(str(data))

def append_to_csv(df,filename):
    with open(filename, 'a') as f:
        df.to_csv(f, mode='a', header=f.tell()==0,index=False)

info = get_info()

bearer_token=info["bearer_token"]
api_key=info["api_key"]
api_key_secret=info["api_key_secret"]
access_token=info["access_token"]
access_token_secret=info["access_token_secret"]
my_user_id=info["user_id"]
my_username=info["username"]

last_seen_id = read_file(last_seen_file)

tweet_columns = ["query_id","tweet_id","created_at","content","likes","comments","retweets","quotes","cashtag","additional_mention","address_asked","author_id","author_username","followers","following","tweets","verified","action"]
tweet_data = pd.DataFrame(columns=tweet_columns)

query_columns = ["query_id","query","result_count","oldest_id","newest_id","query_at","ignored","done"]
query_data = pd.DataFrame(columns=query_columns)

client=tweepy.Client(bearer_token=bearer_token,consumer_key=api_key,consumer_secret=api_key_secret,
                    access_token=access_token,access_token_secret=access_token_secret,wait_on_rate_limit=True)

keywords = ['giveaway OR giveaways','airdrop OR airdrops']
hashtags = ['nft','crypto','eth','btc','shib','sol',]

currencies = '(nft OR crypto OR shib OR doge OR eth OR ethereum OR btc OR bitcoin OR sol OR solana OR bnb OR binance OR matic OR polygon OR ftm OR fantom)'
identifiers = '(nftdrop OR nftairdrop OR airdropping OR airdrop OR airdrops OR nftgiveaway OR giveaways OR giveaway OR give OR giving OR want)'
additional = '-🔔 -buy -buyer -buyers -unsold -pin -pinned -📌 (((like OR ❤️) follow) OR ((retweet OR rt) follow) OR ((retweet OR rt) (like OR ❤️))) -dao lang:en -is:retweet -is:reply -is:quote -has:links'

query = ' '.join([currencies,identifiers,additional])

max_results = 100
expansions = ["referenced_tweets.id.author_id"]
tweet_fields = ["author_id","created_at","source","in_reply_to_user_id","entities","public_metrics"]
user_fields = ["username","public_metrics","verified"]

reply = "Check this out guys "
reply_address = "Check this out guys \nWallet Address: "

pages=tweepy.Paginator(client.search_recent_tweets,query=query,max_results=max_results,expansions=expansions,
                        tweet_fields=tweet_fields,user_fields=user_fields,since_id=last_seen_id)


query_id = read_file(query_id_file)
result_count = 0
query_at = time.gmtime()
ignored = 0
done = 0 

for i,page in enumerate(pages):
    tweets = page.data
    users={u["id"]:u for u in page.includes["users"]}

    result_count += page.meta["result_count"]
    oldest_id = page.meta["oldest_id"]
    if i==0:
        newest_id = page.meta["newest_id"]

    for tweet in tweets:

        tweet_id = tweet.id
        created_at = tweet.created_at
        content = tweet.text
        likes = tweet.public_metrics["like_count"]
        comments = tweet.public_metrics["reply_count"]
        retweets = tweet.public_metrics["retweet_count"]
        quotes = tweet.public_metrics["quote_count"]

        address_asked = False
        address_synonyms = ["wallet","wallets","address","addresses"]

        for word in content.split():
            if word.lower() in address_synonyms:
                address_asked=True

        cashtag = False
        additional_mention = []

        if tweet.entities is not None:
            if 'cashtags' in tweet.entities.keys():
                cashtag=True
            if 'mentions' in tweet.entities.keys():
                    for mention in tweet.entities['mentions']:
                        if(mention['username']!=users[tweet.author_id].username):
                            additional_mention.append(mention['username'])

        additional_mention=set(additional_mention)
        additional_mention=list(additional_mention)


        author_id = tweet.author_id
        author_username = users[tweet.author_id].username
        followers = users[tweet.author_id].public_metrics["followers_count"]
        following = users[tweet.author_id].public_metrics["following_count"]
        tweet_count = users[tweet.author_id].public_metrics["tweet_count"]
        verified = users[tweet.author_id].verified

        action = "ignore"

        if (verified or followers>4000):
            ignored-=1
            try:
                if address_asked:
                    client.create_tweet(in_reply_to_tweet_id=tweet.id,text=reply_address)
                else:
                    client.create_tweet(in_reply_to_tweet_id=tweet.id,text=reply)
                client.retweet(tweet_id=tweet.id)
                client.like(tweet_id=tweet.id)
                client.follow_user(target_user_id=tweet.author_id)
                if len(additional_mention)<2:
                    for username in additional_mention:
                        userid=client.get_user(username=username).data['id']
                        client.follow_user(target_user_id=userid)
                action = "done"
                done+=1
            except tweepy.TweepyException as e:
                continue

        tweet_data.loc[len(tweet_data)] = [query_id,tweet_id,created_at,content,likes,comments,retweets,quotes,cashtag,additional_mention,address_asked,author_id,author_username,followers,following,tweet_count,verified,action]

ignored += result_count
query_data.loc[0] = [query_id,query,result_count,oldest_id,newest_id,query_at,ignored,done]

save_to_file(last_seen_file,newest_id)
save_to_file(query_id_file,query_id+1)

append_to_csv(tweet_data,current_dir+tweet_data_file)
append_to_csv(query_data,current_dir+query_data_file)

print(result_count)