import time
from craigslist import CraigslistHousing
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import sessionmaker
from dateutil.parser import parse
from util import find_points_of_interest
from slackclient import SlackClient
import settings

# Database connection
DBEngine = create_engine('sqlite:///listings.db', echo=False)
Base = declarative_base()

class Listing(Base):
    """
    A table to store data on craigslist listings.
    """

    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True)
    link = Column(String, unique=True)
    created = Column(DateTime)
    geotag = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    name = Column(String)
    price = Column(Float)
    location = Column(String)
    cl_id = Column(Integer, unique=True)
    area = Column(String)
    bart_stop = Column(String)

Base.metadata.create_all(DBEngine)

Session = sessionmaker(bind=DBEngine)
session = Session()

class Scraper:
    """
    A scraper class that will pull data from Craigslist and match with the
    criteria.
    """
    def __init__(self, site, category, areas_filters_dict,
                 slack_settings):
        """
        Initializes and instance of this class.
        :param site: The Craigslist site to search.
        :param category: The category of the housing search.
        :param areas_filters_dict: A dictionary of areas with filters to search.
        """
        # Create Craigslist clients for each area
        self.cl_clients = {}
        for area, filters in areas_filters_dict.items():
            self.cl_clients[area] = CraigslistHousing(site=site,
                                                      category=category,
                                                      area=area,
                                                      filters=filters)

        # Create a Slack client to post satisfying listings to
        self.slack_client = SlackClient(slack_settings["slack_token"])
        self.slack_channel = slack_settings["slack_channel"]

    def scrape_area(self, area):
        """
        Scrapes craigslist for a certain geographic area, and finds 
        the latest listings.
        :param area:
        :return: A list of results.
        """
        # Get the latest listing on Craigslist
        listings = self.cl_clients[area].get_results(sort_by='newest',
                                                      geotagged=True,
                                                      limit=20)
        results = []

        for listing in listings:
            print(listing)

        return results

    # def scrape_area(self, area):
    #     """
    #     Scrapes craigslist for a certain geographic area, and finds 
    #     the latest listings.
    #     :param area:
    #     :return: A list of results.
    #     """

    #     results = []
    #     gen = cl_h.get_results(sort_by='newest', geotagged=True, limit=20)
    #     while True:
    #         try:
    #             result = next(gen)
    #         except StopIteration:
    #             break
    #         except Exception:
    #             continue
    #         listing = session.query(Listing).filter_by(cl_id=result["id"]).first()

    #         # Don't store the listing if it already exists.
    #         if listing is None:
    #             if result["where"] is None:
    #                 # If there is no string identifying which neighborhood the result is from, skip it.
    #                 continue

    #             lat = 0
    #             lon = 0
    #             if result["geotag"] is not None:
    #                 # Assign the coordinates.
    #                 lat = result["geotag"][0]
    #                 lon = result["geotag"][1]

    #                 # Annotate the result with information about the area it's in and points of interest near it.
    #                 geo_data = find_points_of_interest(result["geotag"], result["where"])
    #                 result.update(geo_data)
    #             else:
    #                 result["area"] = ""
    #                 result["bart"] = ""

    #             # Try parsing the price.
    #             price = 0
    #             try:
    #                 price = float(result["price"].replace("$", ""))
    #             except Exception:
    #                 pass

    #             # Create the listing object.
    #             listing = Listing(
    #                 link=result["url"],
    #                 created=parse(result["datetime"]),
    #                 lat=lat,
    #                 lon=lon,
    #                 name=result["name"],
    #                 price=price,
    #                 location=result["where"],
    #                 cl_id=result["id"],
    #                 area=result["area"],
    #                 bart_stop=result["bart"]
    #             )

    #             # Save the listing so we don't grab it again.
    #             session.add(listing)
    #             session.commit()

    #             # Return the result if it's near a bart station, or if it is in an area we defined.
    #             if len(result["bart"]) > 0 or len(result["area"]) > 0:
    #                 results.append(result)

    #     return results

    def scrape(self):
        """
        Runs the Craigslist scraper, and posts data to slack.
        """

        # Get all the results from craigslist.
        all_results = []
        for area in self.cl_clients.keys():
            all_results += self.scrape_area(area)

        print("{}: Got {} results".format(time.ctime(), len(all_results)))

        # Post each result to slack.
        for result in all_results:
            self.post_listing_to_slack(result)

    def post_listing_to_slack(self, result):
        """
        Posts the result to Slack channel.
        :param result: The result to post to Slack channel.
        """
        # Build the description string to post
        desc = "{0} | {1} | {2} | {3} | <{4}>".format(listing["area"],
                                                      listing["price"],
                                                      listing["bart_dist"],
                                                      listing["name"],
                                                      listing["url"])

        # Post to Slack
        self.slack_client.api_call("chat.postMessage",
                                   channel=self.slack_channel,
                                   text=desc,
                                   username='pybot',
                                   icon_emoji=':robot_face:')

if "__main__" == __name__:
    print("Hello son!")
    areas_filters_dict = {
        "see": {"max_price": 800}
    }

    slack_settings = {
        "slack_token": "ABC",
        "slack_channel": "housing"
    }

    scraper = Scraper(site="seattle",
                      category="roo",
                      areas_filters_dict=areas_filters_dict,
                      slack_settings=slack_settings)
    
    scraper.scrape()
