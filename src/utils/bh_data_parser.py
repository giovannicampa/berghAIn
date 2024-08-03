import argparse
import os

from datetime import datetime
from glob import glob

import pandas as pd

from bs4 import BeautifulSoup

from src.utils.club_data_parser import ClubParser


class BHParser(ClubParser):
    def __init__(self, club_name: str = "Berghain", club_page_url="https://www.berghain.berlin/en/program/archive"):
        ClubParser.__init__(self, club_name=club_name, club_page_url=club_page_url)
        self.locations = ["Berghain", "Italorama Bar", "Panorama Bar", "Säule"]

    def extract_content_from_page(self, url_to_parse: str):
        """
        Parses the url for a club's website and returns the DJ's followers and meta data.
        """

        html_content = self.request_website(url_to_parse)

        soup = BeautifulSoup(html_content, "html.parser")
        links = soup.select("a")

        historical_data = []

        for link in links:
            party_location = None
            for location in self.locations:
                if location in link.text and "upcoming-event" in str(link):
                    party_location = location
                    break
            if party_location is None:
                continue

            date_string = link.text.split("\n")[4].replace(" ", "")
            date_object = datetime.strptime(date_string, "%d.%m.%Y").date()
            artist_str = link.contents[-2].text  # Panoramabar
            artist_str = artist_str.replace("\n", "")
            artist_str = artist_str.replace("   ", "")
            artist_str = artist_str.replace("Live", "")
            artist_str = artist_str.replace(" B2B ", ",")
            artist_str = artist_str.replace(" b2b ", ",")

            artists = artist_str.split(",")

            for artist in artists:
                artist_data = {}

                artist_data["date"] = date_object
                artist_data["name"] = artist
                artist_data["followers"] = self.parse_followers(artist)
                artist_data["location"] = party_location

                historical_data.append(artist_data)

        return pd.DataFrame(historical_data)

    def extract_and_save_all(self, year_list: list[int] = None) -> pd.DataFrame:
        """
        Extracts and saves the
        """
        data = []
        for year in year_list:

            existing_data = glob(os.path.join("data", self.club_name, self.sc_folder_name) + f"*/{year}*.csv")
            existing_months = [int(i[-6:-4]) for i in existing_data]

            for month in range(1, 13):
                if month in existing_months: continue
                print(f"Currently processing {year}/{month}")
                month_frmt = (str(month)).zfill(2)
                url_to_parse = f"{self.club_page_url}/{year}/{month_frmt}/"
                data_month = self.extract_content_from_page(url_to_parse)
                self.save_data(data_month, year, month_frmt)
                data.append(data_month)

        data = pd.concat(data)

        return data

    def get_followers_at_date(self, date: datetime.date):
        """
        Given a date, it finds the corresponding follower number
        """

        month_frmt = (str(date.month)).zfill(2)
        location_dates_data = os.path.join(
            "data", self.club_name, self.sc_folder_name, f"{date.year}_{month_frmt}.csv"
        )
        if not os.path.exists(location_dates_data):
            url_to_parse = f"{self.club_page_url}/{date.year}/{month_frmt}/"
            data_month = self.extract_content_from_page(url_to_parse)
            self.save_data(data_month, date.year, month_frmt)
        else:
            data_month = pd.read_csv(location_dates_data, index_col=0, parse_dates=["date"])

        data_month.date = data_month.date.dt.date

        index_today = data_month.date == date
        artists_data = data_month[index_today]
        if sum(index_today) == 0:
            print("No event found for today")
            return None
        else:
            followers = artists_data.followers.sum()
            return followers, artists_data

    def generate_path(self, year: int, month: int):
        return os.path.join("data", self.club_name, self.sc_folder_name, f"{year}_{month}.csv")

    def save_data(self, data_month: pd.DataFrame, year: int, month_frmt: str):
        """
        Saves the data at the corresponding path
        """
        path = self.generate_path(year, month_frmt)
        data_month.to_csv(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=str, nargs="+", default=["2024"])
    args =  parser.parse_args()

    bh_parser = BHParser(club_name="Berghain", club_page_url="https://www.berghain.berlin/en/program/archive")
    data = bh_parser.extract_and_save_all(year_list=args.years)
    data.to_csv(os.path.join("data", bh_parser.club_name, bh_parser.sc_folder_name, "test_data.csv"))
