import glob
import os
import pandas as pd

from abc import ABC
from urllib.request import urlopen

import requests
from bs4 import BeautifulSoup


class ClubParser(ABC):
    """
    Abstract base class for parsing data from a club's website and looking up
    artists' data on SoundCloud.

    This class defines the interface that concrete club parser classes should
    implement. Concrete classes should provide methods for extracting event
    information from the club's website and looking up artists' data on SoundCloud.
    """

    def __init__(self, club_name=str, club_page_url=str):
        self.sc_folder_name = "soundcloud_followers"
        self.club_name = club_name.lower()
        self.path_to_data = os.path.join("data", self.club_name, self.sc_folder_name)
        self.club_page_url = club_page_url

    def request_website(self, url: str):
        """Requests the website"""
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors (e.g., 404)
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error fetching content: {e}")
            return None

    @staticmethod
    def preprocess_artist_name(artist: str) -> str:
        return artist.replace(" ", "").lower()

    def parse_followers(self, artist: str) -> int:
        """
        Given an artist name extracted from the club's website, it looks for the artist's soundcloud page and
        extracts the number of followers.

        Args:
            artist: name of the artist

        Returns:
            followers: number of followers
        """

        # artist = self.preprocess_artist_name(artist)

        # url_to_parse = f"https://soundcloud.com/search/people?q={artist}" TODO: use the search for people
        url_to_parse = f"https://soundcloud.com/search?q={artist}"
        html_content = self.request_website(url_to_parse)
        soup = BeautifulSoup(html_content, "html.parser")

        links = soup.select("a")
        artist_tag = links[6]["href"]
        artist_tag = artist_tag.replace("/", "")

        try:
            page = urlopen(f"https://soundcloud.com/{artist_tag}")
            html_bytes = page.read()
            html = html_bytes.decode("utf-8")

            index_start = html.find('follower_count" content="') + len('follower_count" content="')
            index_end = html.find('">\n<link rel="canonical')

            followers = int(html[index_start:index_end])
        except:
            return 0

        return followers

    def gather_artist_data(self, path_to_data: str = None) -> pd.DataFrame:
        """
        Load data previously saved data

        Args:
            path_to_data: path to the folder with the csv files. If not set, the default path is used

        Returns:
            followers_by_date: data of the followers number grouped by evening.
        """

        if path_to_data is None:
            path_to_data = self.path_to_data
        files = glob.glob(os.path.join(path_to_data, "*.csv"))
        files = [file_name for file_name in files if "test" not in file_name]

        data = []
        followers_by_date = []

        for path in files:
            df = pd.read_csv(path)
            data.append(df)

        data = pd.concat(data)

        for date in data.date.unique():
            followers = data[data.date == date].followers.sum()
            followers_by_date.append({"date": pd.Timestamp(date), "followers": followers})

        followers_by_date = pd.DataFrame(followers_by_date)

        followers_by_date.sort_values("date", inplace=True)
        return followers_by_date

    def extract_content_from_page(self, url: str):
        """
        Abstract method to parse event information from the club's single website.
        """
        pass

    def extract_and_save_all(self) -> pd.DataFrame:
        """
        Abstract method to get and save all data from a specific club's website.
        """
        pass
