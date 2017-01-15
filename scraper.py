import time
from craigslist import CraigslistHousing
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import sessionmaker
from dateutil.parser import parse
import location_helper
from slackclient import SlackClient
import settings
from condition import Condition, LocationCondition

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

        # Initialize filtering conditions
        self.conditions = []

    def add_condition(self, condition):
        """
        Adds the filtering condition to weed out listings.
        """
        # Data validation
        if condition is None or not isinstance(condition, Condition):
            print("Condition is not well defined.")
            return

        # Add the condition
        self.conditions.append(condition)

    def scrape(self):
        """
        Runs the Craigslist scraper, and posts data to slack.
        """

        # Get all the results from craigslist.
        all_results = []
        for area in self.cl_clients:
            all_results += self.scrape_area(area)

        print("{}: Got {} results".format(time.ctime(), len(all_results)))

        # Post each result to slack.
        for result in all_results:
            self.post_listing_to_slack(result)

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

        print("Browsing through the new listings...")

        # Process new listing and check for criteria
        for listing in listings:
            # Skip the listing if it is already in the database
            existing_listing = session.query(Listing).filter_by(cl_id=listing["id"]).first()
            if existing_listing is not None:
                continue

            # Create and save the listing so we don't grab it again.
            listing_entity = self._create_listing_entity(listing)
            session.add(listing_entity)
            session.commit()

            # Update location and transportation information
            listing = self.update_geographic_information(listing)

            # Check the listing against conditions
            is_good_listing = True
            for condition in self.conditions:
                # Continue if the listing satisfies the current condition
                if condition.check(listing):
                    continue

                # Otherwise, mark the listing as bad
                is_good_listing = False
                break

            # Do nothing if it is a bad listing
            if not is_good_listing:
                continue

            # Add the listing to return listings and database
            results.append(listing)

        # Return all the good results
        return results

    def post_listing_to_slack(self, listing):
        """
        Posts the result to Slack channel.
        :param result: The result to post to Slack channel.
        """
        # Data validation
        if listing is not None and not listing:
            print("Warning: The listing is not well defined.")
            return

        # Build the description string to post
        desc = "{} | {} | {} | <{}>".format(listing["area"],
                                            listing["price"],
                                            listing["name"],
                                            listing["url"])

        print("Desc: {}".format(desc))

        # Post to Slack
        self.slack_client.api_call("chat.postMessage",
                                   channel=self.slack_channel,
                                   text=desc,
                                   username='pybot',
                                   icon_emoji=':robot_face:')

    def update_geographic_information(self, listing):
        """
        Updates the geographic information such as location, lattitude,
        longitude and transportation time.
        :param listing: The listing from Craigslist.
        :return: The updated listing result.
        """
        # Data validation
        if listing is not None and not listing:
            print("Warning: The listing is not well defined.")
            return listing
        
        # Try to get the geocode from geotag if present
        if "geotag" in listing and listing["geotag"] is not None:
            listing["lat"] = listing["geotag"][0]
            listing["lon"] = listing["geotag"][1]
            return listing
        
        # Try to deduce the geocode from the locations
        locations = []
        if "where" in listing and listing["where"] is not None:
            locations = location_helper.parse_locations(listing["where"])

        # Calculate the average geocode of all the locations
        avg_lat = 0
        avg_lon = 0
        count = 0
        for location in locations:
            lat, lon = location_helper.get_geocode(location)
            avg_lat += lat
            avg_lon += lon
            count += 1
        listing["lat"] = avg_lat / count
        listing["lon"] = avg_lon / count

        # Return the updated listing
        return listing

    def _create_listing_entity(self, listing):
        """
        Creates a listing entity for database from the listing result.
        :param listing: The listing result from Craigslist.
        :return: The Listing entity for database.
        """
        # Data validation
        if listing is None:
            print("Warning: listing parameter should not be None.")
            return None

        # Parse the lattitude and longitude of the listing result
        has_geotag = listing["geotag"] is not None
        lat = listing["geotag"][0] if has_geotag else 0
        lon = listing["geotag"][1] if has_geotag else 0

        # Try parsing the price
        price = -1
        try:
            price = float(listing["price"].replace("$", ""))
        except OverflowError:
            pass

        # TODO: Clean up the area and bart station
        listing["area"] = "Seattle"

        # Create listing entity
        return Listing(
            link=listing["url"],
            created=parse(listing["datetime"]),
            lat=lat,
            lon=lon,
            name=listing["name"],
            price=price,
            location=listing["where"],
            cl_id=listing["id"],
            area=listing["area"],
        )
