#! /usr/bin/python3

from datetime import datetime, timedelta, date

import json
import praw
import pandas as pd
import sqlalchemy as sa
import pytz

from src.db.create_db_connection import load_db_config, create_connection


def setup_reddit_api(config_file):
    """
    Set up a Reddit bot using provided credentials and parse submissions from a subreddit.

    Parameters:
        config_file (str): Path to the JSON file containing Reddit API credentials.
        date_starting (datetime): Starting date for subreddit submissions.
        date_ending (datetime): Ending date for subreddit submissions.
    
    Returns:
        generator: A generator of submissions from the specified subreddit within the given dates.
    """
    # Load credentials from a JSON file
    with open(config_file, 'r') as file:
        input_data = json.load(file)
    
    # Set up reddit bot
    reddit = praw.Reddit(
        client_id=input_data["client_id"],
        client_secret=input_data["client_secret"],
        username=input_data["username"],
        password=input_data["password"],
        user_agent=input_data["user_agent"]
    )

    return reddit



class DataDownloaderReddit:
    def __init__(self, subreddits=None):
        self.string_size_header = 42
        self.subreddits = subreddits  # "Berghain_Community"

        # Avoid sentences that contain these keywords (still asking myself, why I am getting these in italian...)
        self.blacklist = ["I am a bot", "cancellato", "rimosso", "removed", "deleted"]

        # Read login data for reddit

        self.reddit = setup_reddit_api(config_file="config/reddit_config.json")
        config_path = "config/db_config.json"
        config = load_db_config(config_path)
        self.engine = create_connection(config)

        table_inspector = sa.inspect(self.engine)
        self.reddit_table_names = table_inspector.get_table_names()

        self.berlin_timezone = pytz.timezone('Europe/Berlin')

    @staticmethod
    def create_table_name(symbol: str):
        return f"{symbol}"

    def create_table(self, table_name: str):
        """In case the table for a specific table_name does not exist, it is created."""

        with self.engine.connect() as con:
            table_name = self.create_table_name(table_name)
            q = (
                f"CREATE TABLE clubs.{table_name} ("
                "body LONGTEXT, "
                "datetime DATETIME, "
                "ups INT, "
                "downs INT, "
                "type VARCHAR(255), "
                "id VARCHAR(255), "
                "parent VARCHAR(255))"
            )

            con.execute(sa.text(q))

        self.reddit_table_names.append(table_name)


    def get_reddit_data(
        self, time_oldest_requested: datetime = None, subreddit_name: str = "Berghain_Community", skip_ranges: dict = None
    ) -> pd.DataFrame:
        """Looks for the data from the requested subreddit.
        If it is available, it returns it from the database, otherwise it downloads it, then returns it.

        Args:
            - time_oldest_requested: does not return data older than this
            - subreddit_name: name of the subreddit

        Returns:
            - dataframe of reddit data, either downloaded or from database
        # TODO: integrate skip_range in get_reddit_data
        """

        time_oldest_requested = self.berlin_timezone.localize(time_oldest_requested)

        subreddit_table_name = f"reddit_{subreddit_name}"

        symbol_table_exists = any(
            [self.create_table_name(subreddit_table_name) == table for table in self.reddit_table_names]
        )

        if not symbol_table_exists:
            self.create_table(subreddit_table_name)

        query_data = f"SELECT * FROM clubs.{subreddit_table_name}"
        data_in_table = pd.read_sql(sa.text(query_data), con=self.engine.connect())

        time_reddit_newest = pd.to_datetime(data_in_table.datetime.max())
        if pd.isna(time_reddit_newest):
            time_reddit_newest = datetime.now() - timedelta(30)

        # Localize the naive datetime object to the Berlin timezone
        time_reddit_newest = self.berlin_timezone.localize(time_reddit_newest)


        time_reddit_oldest = pd.to_datetime(data_in_table.datetime.min())
        if pd.isna(time_reddit_oldest):
            time_reddit_oldest = datetime.now() - timedelta(31)

        # Localize the naive datetime object to the Berlin timezone
        time_reddit_oldest = self.berlin_timezone.localize(time_reddit_oldest)

        if pd.isna(time_reddit_oldest):
            time_reddit_oldest = datetime.now() - timedelta(30)

        # If data is up-to-date return it as is, no need to download
        existing_relevant = data_in_table[
            (data_in_table.datetime >= time_oldest_requested.date()) & (data_in_table.datetime <= datetime.now().date())
        ]

        # If there is no data, or if there are gaps, I need to get said data
        if len(existing_relevant.datetime.unique()) == (datetime.now().date() - time_oldest_requested.date()).days:
            return data_in_table

        gen = self.reddit.subreddit(subreddit_name).new(limit=10000)

        # Keeping track of the initiated hours
        time_list = []
        submissions_all = []

        # Iterate over posts. Assuming the data starts from the newest to the oldest
        for submission in gen:
            submissions = []

            # Localize the UTC time and then convert to Berlin time
            utc_time = pytz.utc.localize(datetime.utcfromtimestamp(submission.created_utc))
            time_stamp = utc_time.astimezone(self.berlin_timezone)

            if skip_ranges and any(
                [
                    time_stamp.date() >= skip_range["earliest"] and time_stamp.date() <= skip_range["latest"]
                    for skip_range in skip_ranges
                ]
            ):
                continue

            if not time_stamp in time_list:
                time_list.append(time_stamp)
                print(f"Analyzing new hour: {time_stamp}", end="\r")

            # Filtering out non related posts or irrelevant submissions
            if not "queue" in submission.title.lower():
                continue
            # If the data I am getting is older than the newest I already have in the database, then I can quit
            elif time_stamp < time_reddit_newest and time_stamp > time_reddit_oldest:
                continue
            # Data not older than this tate
            elif time_stamp < time_oldest_requested:
                break

            # Reading the title and the upvotes and write them to file
            title_data = {
                "datetime": time_stamp,
                "type": "title",
                "body": submission.title,
                "ups": submission.ups,
                "downs": submission.downs,
                "id": submission.id,
                "parent": None,
            }

            submissions.append(title_data)
            submissions_all.append(title_data)

            # Iterating over comments in the current post
            for comment in submission.comments:
                # Skipping the end of readeable comments
                if "MoreComments" in str(type(comment)):
                    break

                # Skip empty comments of comments with a little amount of upvotes (10) --> Not relevant input
                if (
                    any(string in comment.body for string in self.blacklist)
                    or comment.body == ""
                    or "used to indicate a person  thing  idea  state  event" in comment.body
                ):
                    continue

                # Localize the UTC time and then convert to Berlin time
                utc_time = pytz.utc.localize(datetime.utcfromtimestamp(comment.created_utc))
                time_stamp = utc_time.astimezone(self.berlin_timezone)

                comment_data = {
                    "datetime": time_stamp,
                    "type": "comment",
                    "body": comment.body,
                    "ups": comment.ups,
                    "downs": comment.downs,
                    "id": comment.id,
                    "parent": comment.parent_id,
                }

                submissions.append(comment_data)
                submissions_all.append(comment_data)

            data = pd.DataFrame(submissions)
            print(f"Written {data.shape[0]} rows to table")
            data.to_sql(name=subreddit_table_name, con=self.engine, if_exists="append", index=False)

        data_new = pd.DataFrame(submissions_all)
        data_all = pd.concat([data_in_table, data_new], ignore_index=True)
        data_all = data_all[(data_all.datetime >= time_oldest_requested)]

        return data_all

    def get_saved_data_reddit(self) -> pd.DataFrame:
        """
        Checks if data is already available or if it needs to be downloaded.

        The data contains the text from comments and titles.

        Returns:
            - data_reddit: dataframe with the reddit comments and titles
        """

        subreddit_table_name = f"reddit_Berghain_Community"
        query_data = f"SELECT * FROM clubs.{subreddit_table_name}"

        symbol_table_exists = any(
            [self.create_table_name(subreddit_table_name) == table for table in self.reddit_table_names]
        )

        if not symbol_table_exists:
            self.create_table(subreddit_table_name)

        data = pd.read_sql(sa.text(query_data), con=self.engine.connect())

        data.sort_values("datetime", inplace=True)
        return data


if __name__ == "__main__":
    subreddit = "Berghain_Community"
    downloader = DataDownloaderReddit([subreddit])
    data = []
    oldest = datetime.now() - timedelta(365*4)
    data_subreddit = downloader.get_reddit_data(subreddit_name=subreddit, time_oldest_requested=oldest)
    data.append(data_subreddit)

    data = pd.concat(data, ignore_index=True)

    print("done")