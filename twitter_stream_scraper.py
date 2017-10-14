import urllib2
import datetime
from abc import ABCMeta
from urllib import urlencode
from abc import abstractmethod
from urlparse import urlunparse
from bs4 import BeautifulSoup
from time import sleep
import jsonpickle
import json


__author__ = 'Lucas Santos'


class TwitterStream:

    __metaclass__ = ABCMeta

    def __init__(self, rate_delay, error_delay=5):
        """
        :param rate_delay: How long to pause between calls to Twitter
        :param error_delay: How long to pause when an error occurs
        """
        self.rate_delay = rate_delay
        self.error_delay = error_delay

    def search(self, category, file_name):
        """
        Scrape items from twitter
        :param category: Category to search Twitter with. Accordint to initial page: https://twitter.com
        """
        url = self.construct_url(category)
        continue_search = True
        min_tweet = None
        response = self.execute_search(url)
        while response is not None and continue_search and response['items_html'] is not None:
            tweets_id, tweets = self.parse_tweets(response['items_html'])

            # If we have no tweets, then we can break the loop early
            if len(tweets) == 0:
                break

            continue_search = self.save_tweets(tweets, file_name)
            # Try to capture maximum tweets as possible, passing as parameter
            # the last 10 tweets.
            max_position = "{\"seenTweetIDs\":%s,\"servedRangeOption\":{\"bottom\":%s, \"top\":%s}}" % (
                tweets_id[-10:-1], tweets_id[-1], tweets_id[-1])
            max_position = str.replace(max_position, " ", "")
            max_position = str.replace(max_position, "'", "")
            url = self.construct_url(
                category, max_position=max_position).replace("?", "", 1)
            # Sleep for our rate_delay
            sleep(self.rate_delay)
            response = self.execute_search(url)

    def execute_search(self, url):
        """
        Executes a search to Twitter for the given URL
        :param url: URL to search twitter with
        :return: A HTML object with data from Twitter
        """
        try:
            # Specify a user agent to prevent Twitter from returning a profile
            # card
            headers = {
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36'
            }
            req = urllib2.Request(url, headers=headers)
            response = urllib2.urlopen(req)
            data = json.loads(response.read())
            return data

        # If we get a ValueError exception due to a request timing out, we sleep for our error delay, then make
        # another attempt
        except ValueError as e:
            print(e.message)
            print("Sleeping for %i" % self.error_delay)
            sleep(self.error_delay)
            return self.execute_search(url)

    @staticmethod
    def parse_tweets(items_html):
        """
        Parses Tweets from the given HTML
        :param items_html: The HTML block with tweets
        :return: A JSON list of tweets
        """
        soup = BeautifulSoup(items_html, "html")
        tweets = []
        tweets_id = []
        for div in soup.find_all("div", class_='js-stream-tweet'):

            # If our div doesn't have a tweet-id, we skip it as it's not going
            # to be a tweet.
            if 'data-tweet-id' not in div.attrs:
                continue

            tweets_id.append(div['data-tweet-id'])

            tweet = {
                'tweet_id': div['data-tweet-id'],
                'text': None,
                'user_id': None,
                'user_screen_name': None,
                'user_name': None,
                'created_at': None,
                'retweets': 0,
                'favorites': 0
            }

            # Tweet Text
            text_p = div.find("p", class_="tweet-text")
            if text_p is not None:
                tweet['text'] = text_p.get_text()

            # Tweet User ID, User Screen Name, User Name
            user_details_div = div.find("div", class_="original-tweet")
            if user_details_div is not None:
                tweet['user_id'] = user_details_div['data-user-id']
                tweet['user_screen_name'] = user_details_div['data-user-id']
                tweet['user_name'] = user_details_div['data-name']

            # Tweet date
            date_span = div.find("span", class_="_timestamp")
            if date_span is not None:
                tweet['created_at'] = float(date_span['data-time-ms'])

            # Tweet Retweets
            retweet_span = div.select(
                "span.ProfileTweet-action--retweet > span.ProfileTweet-actionCount")
            if retweet_span is not None and len(retweet_span) > 0:
                tweet['retweets'] = int(
                    retweet_span[0]['data-tweet-stat-count'])

            # Tweet Favourites
            favorite_span = div.select(
                "span.ProfileTweet-action--favorite > span.ProfileTweet-actionCount")
            if favorite_span is not None and len(retweet_span) > 0:
                tweet['favorites'] = int(
                    favorite_span[0]['data-tweet-stat-count'])

            tweets.append(tweet)
        return (tweets_id, tweets)

    @staticmethod
    def construct_url(category, max_position=None):
        """
        For a given category, will construct a URL to search Twitter with
        :param category: The category term used to search twitter
        :param max_position: The max_position value to select the next pagination of tweets
        :return: A string URL
        """

        # If our max_position param is not None, we add it to the parameters
        params = dict()
        if max_position is not None:
            params['include_available_features'] = 1
            params['include_entities'] = 1
            params['max_position'] = max_position
            params['reset_error_state'] = 'false'

        url_tupple = ('https', 'twitter.com', '/i/streams/category/' +
                      category+'/timeline?', '', urlencode(params), '')
        return urlunparse(url_tupple)

    @abstractmethod
    def save_tweets(self, tweets):
        """
        An abstract method that's called with a list of tweets.
        When implementing this class, you can do whatever you want with these tweets.
        """


class TwitterSearchImpl(TwitterStream):

    def __init__(self, rate_delay, error_delay, max_tweets):
        """
        :param rate_delay: How long to pause between calls to Twitter
        :param error_delay: How long to pause when an error occurs
        :param max_tweets: Maximum number of tweets to collect for this example
        """
        super(TwitterSearchImpl, self).__init__(rate_delay, error_delay)
        self.max_tweets = max_tweets
        self.counter = 0

    def save_tweets(self, tweets, file_name):
        """
        Just prints out tweets
        :return:
        """

        f = open(file_name+".json", 'a+')

        for tweet in tweets:
            # Lets add a counter so we only collect a max number of tweets
            self.counter += 1

            if tweet['created_at'] is not None:
                t = datetime.datetime.fromtimestamp((tweet['created_at']/1000))
                fmt = "%Y-%m-%d %H:%M:%S"
                f.write(jsonpickle.encode(tweet, unpicklable=False) +
                        '\n')
                print("%i [%s] -" % (self.counter, t.strftime(fmt)))

            # When we've reached our max limit, return False so collection
            # stops

            if self.counter >= self.max_tweets:
                return False

        return True
        f.close()

if __name__ == '__main__':

    twit = TwitterSearchImpl(3, 5, 10000)
    # twit.search("687094900836274198","stream_entertaining")
    # twit.search("687094900836274187","stream_politics")
    # twit.search("798288329506598913","stream_sports")
    # twit.search("798245663997734912","stream_fun")
    # twit.search("687094900836274204","stream_music")
    twit.search("691837024001662976", "stream_style")
