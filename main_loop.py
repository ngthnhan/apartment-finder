from scraper import Scraper
from condition import LocationCondition
import settings
import time
import sys
import traceback

if "__main__" == __name__:
    # Define areas to search for with accompanying filters
    areas_filters_dict = {
        "see": {"max_price": 800, "min_price": 400}
    }

    # Define slack settings
    slack_settings = {
        "slack_token": "ABC",
        "slack_channel": "housing"
    }

    # Initialize scraper
    scraper = Scraper(site="seattle",
                      category="roo",
                      areas_filters_dict=areas_filters_dict,
                      slack_settings=slack_settings)

    # Initialize filtering conditions
    scraper.add_condition(LocationCondition())

    # Main loop to scrape info and post new matching listings
    while True:
        print("{}: Starting scrape cycle".format(time.ctime()))
        try:
            scraper.scrape()
        except KeyboardInterrupt:
            print("Exiting....")
            sys.exit(1)
        except Exception as exc:
            print("Error with the scraping:", sys.exc_info()[0])
            traceback.print_exc()
        else:
            print("{}: Successfully finished scraping".format(time.ctime()))
        time.sleep(settings.SLEEP_INTERVAL)
