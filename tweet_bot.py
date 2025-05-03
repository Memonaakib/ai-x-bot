#!/usr/bin/env python3
import os, time, json, re, argparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import tweepy, feedparser, nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

nltk_data_path = os.getenv("NLTK_DATA", "/home/runner/nltk_data")
nltk.data.path.insert(0, nltk_data_path)

# Bot Constants
HISTORY_FILE = "usage.json"
CACHE_HOURS = 48
VIRAL_KEYWORDS = ['breaking', 'latest', 'alert', 'exclusive', 'india', 'israel', 'gaza', 'pakistan', 'us']

class AIXBot:
    def __init__(self):
        nltk.download('stopwords', download_dir=nltk_data_path, quiet=True)
        self.stop_words = set(stopwords.words('english'))

        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET")
        )

        self.usage_data = self.load_history()
        self.posted = self.usage_data.get('posted', {})
        self.last_post_time = self.usage_data.get('last_post_time', 0)
        self.min_interval = 3600  # Post gap: 1 hour

    def load_history(self):
        try:
            with open(HISTORY_FILE) as f:
                data = json.load(f)
            cutoff = datetime.now() - timedelta(hours=CACHE_HOURS)
            data['posted'] = {k:v for k,v in data.get('posted', {}).items() if datetime.fromisoformat(v)>cutoff}
            return data
        except:
            return {'posted':{}, 'last_post_time':0}

    def save_history(self):
        self.usage_data['posted'] = self.posted
        self.usage_data['last_post_time'] = self.last_post_time
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.usage_data, f, indent=2)

    def clean(self, text):
        tokens = word_tokenize(text.lower())
        return ' '.join([t for t in tokens if t.isalnum() and t not in self.stop_words])

    def is_viral(self, title):
        cleaned = self.clean(title)
        return any(re.search(rf"\\b{kw}\\b", cleaned) for kw in VIRAL_KEYWORDS)

    def fetch_headlines(self, url):
        feed = feedparser.parse(url)
        return [entry.title for entry in feed.entries[:5]]

    def run(self, max_posts=1):
        with open('sources.txt') as f:
            sources = [l.strip() for l in f if l.strip()]

        headlines = []
        with ThreadPoolExecutor(max_workers=3) as ex:
            for titles in ex.map(self.fetch_headlines, sources):
                headlines.extend(titles)

        # Filter unique headlines and rank by virality
        unique = list(dict.fromkeys(headlines))
        viral = [h for h in unique if self.is_viral(h)]

        posted = 0
        for title in viral:
            if time.time() - self.last_post_time < self.min_interval:
                break
            tweet = f"🧠 BREAKING: {title}"
            self.client.create_tweet(text=tweet)
            self.last_post_time = time.time()
            posted += 1
            if posted >= max_posts:
                break

        self.save_history()
        print(f"Posted {posted} headline(s)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-posts', type=int, default=1)
    args = parser.parse_args()
    bot = AIXBot()
    bot.run(max_posts=args.max_posts)
