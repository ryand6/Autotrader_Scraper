from urllib.request import urlopen
import csv
import argparse
import datetime
import time
from bs4 import BeautifulSoup


def parse_args():
    """Parse user arguments that specify search criteria for the site"""
    parser = argparse.ArgumentParser(
        description='Scrape Autotrader for used cars based on command line result specifications',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('postcode',
                        type=str,
                        help='Input postcode for searches')

    parser.add_argument('-re',
                        '--results',
                        metavar='results',
                        type=int,
                        help='Maximum number of search pages to return data for',
                        default=100)

    parser.add_argument('-r',
                        '--radius',
                        metavar='radius',
                        type=int,
                        help='Maximum radius from current location for searches',
                        default='1500')

    parser.add_argument('-m',
                        '--make',
                        metavar='make',
                        help='Vehicle make(s)',
                        nargs='*')

    parser.add_argument('-mip',
                        '--minprice',
                        metavar='min price',
                        type=int,
                        help='Minimum price for vehicle')

    parser.add_argument('-map',
                        '--maxprice',
                        metavar='max price',
                        type=int,
                        help='Maximum price for vehicle')

    parser.add_argument('-ml',
                        '--mileage',
                        metavar='mileage',
                        type=int,
                        help='Maximum mileage for vehicle')

    parser.add_argument('-miy',
                        '--minyear',
                        metavar='min year',
                        type=int,
                        help='Minimum price of vehicle')

    parser.add_argument('-may',
                        '--maxyear',
                        metavar='max year',
                        type=int,
                        help='Maximum price of vehicle')

    parser.add_argument('-g',
                        '--gearbox',
                        metavar='gearbox',
                        type=str,
                        help='Type of gearbox')

    parser.add_argument('-e',
                        '--exclude',
                        help='Exclude writeoff categories',
                        action='store_true')

    args = parser.parse_args()

    currentyear = datetime.date.today().year
    gear_options = ("Automatic", "Manual")

    args.postcode = args.postcode.strip().replace(" ", "")

    if args.results < 1 or args.results > 100:
        parser.error(f'--results "{args.results}" must be > 0 and <= 100')

    if args.radius < 1 or args.radius > 1500:
        parser.error(f'--radius "{args.radius}" must be > 0 and <= 1500')

    if args.minprice:
        if args.minprice < 0:
            parser.error(f'--minprice "{args.minprice}" must be >= 0')

    if args.maxprice:
        if args.maxprice < 1:
            parser.error(f'--maxprice "{args.maxprice}" must be >= 1')

    if args.mileage:
        if args.mileage < 1:
            parser.error(f'--mileage "{args.mileage}" must be >= 1')

    if args.make:
        vehicle_makes = []
        with open("vehiclemakes.txt") as infile:
            for line in infile:
                vehicle_makes.append(line.strip())
        for make in args.make:
            if make.capitalize() not in vehicle_makes:
                parser.error(f'--make "{make}" not found in accepted list of vehicle makes. Accepted makes are: {vehicle_makes}')

    if args.minyear:
        if args.minyear < 1920 or args.minyear > currentyear:
            parser.error(f'--minyear "{args.minyear}" must be >= 1920 and <= the current year')

    if args.maxyear:
        if args.maxyear < 1920 or args.maxyear > currentyear:
            parser.error(f'--maxyear "{args.maxyear}" must be >= 1920 and <= the current year')

    if args.gearbox:
        if args.gearbox.capitalize() not in gear_options:
            parser.error(f'--gearbox "{args.gearbox}" must be one of the following options: {gear_options}')

    return args
    

def main():
    """Write the results to a csv file"""
    args = parse_args()

    base_url = 'https://www.autotrader.co.uk/car-search?sort=relevance'

    postcode = f'&postcode={args.postcode}'
    radius = f'&radius={args.radius}'
    minprice = f'&price-from={args.minprice}' if args.minprice else ''
    maxprice = f'&price-to={args.maxprice}' if args.maxprice else ''
    minyear = f'&year-from={args.minyear}' if args.minyear else ''
    maxyear = f'&year-to={args.maxyear}' if args.maxyear else ''
    mileage = f'&maximum-mileage={args.mileage}' if args.mileage else ''
    gearbox = f'&transmission={args.gearbox}' if args.gearbox else ''
    exclude = f'&exclude-writeoff-categories=on' if args.exclude else ''

    search_url = base_url + postcode + radius + minprice + maxprice + minyear + maxyear + mileage + gearbox + exclude

    headers = ["Product Title", "Price (£)", "Reg", "Body Type", "Mileage", "Engine Size", "Engine Power", "Gearbox", "Fuel Type", "Seller Name", "Distance (miles)", "URL"]

    results = []

    with open("results.csv", "w", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(headers)
        if args.make:
            for make in args.make:
                # adjust url if spaces are present 
                make = make.replace(" ", "%20")
                search_url = search_url + f'&make={make}'
                results = results + get_results(search_url, args)
            for result in results:
                writer.writerow(result)
        else:
            results = get_results(search_url, args)
            for result in results:
                writer.writerow(result)


def get_results(initial_url, args):
    """Returns list of details for each product found"""
    all_results = []

    # get number of page results based on users search criteria
    soup = parse_results(initial_url)
    number_of_results = soup.find("li", {"class": "paginationMini__count"}).text.split()
    max_result = number_of_results[3].replace(",", "")
    time.sleep(1)
    # compare page results against users specified number of page results (default 100)
    # ensures that no more than 100 pages are parsed
    if args.results < int(max_result):
        max_result = args.results
    
    for page in range(1, int(max_result) + 1):
        url = initial_url + f'&page={page}'

        soup = parse_results(url)
        vehicles_listings = soup.find_all("li", {"class": "search-page__result"})
        for vehicle in vehicles_listings:
            product_url = vehicle.find("a", {"class": "js-click-handler listing-fpa-link tracking-standard-link"})
            product_url = 'https://www.autotrader.co.uk' + product_url["href"]
            product_car_info = vehicle.find("div", {"class": "product-card-content__car-info"})
            product_section = product_car_info.find("section", {"class": "product-card-details"})
            title = product_section.find("h3", {"class": "product-card-details__title"}).text.strip()
            price = product_car_info.find("div", {"class": "product-card-pricing__price"}).text.strip().replace("£", "").replace(",", "")
            product_specs = []
            specs = product_section.find_all("li", {"class": "atc-type-picanto--medium"})
            for spec in specs:
                product_specs.append(spec.text.strip())
            # skip iteration if there is a lack of product spec information
            if len(product_specs) < 6:
                continue
            reg = product_specs[0]
            body_type = product_specs[1]
            mileage = product_specs[2]
            engine_size = product_specs[3]
            # if number of product specs is over 6, then the engine power spec is likely included
            if len(product_specs) > 6:
                engine_power = product_specs[4]
            if len(product_specs) == 6:
                gearbox = product_specs[4]
            else:
                gearbox = product_specs[5]
            if len(product_specs) == 6:
                fuel_type = product_specs[5]
            else:
                fuel_type = product_specs[6]
            seller_info = vehicle.find("div", {"class": "product-card-seller-info"})
            seller_name = seller_info.find("h3", {"class": "product-card-seller-info__name atc-type-picanto"}).text.strip()
            seller_details = seller_info.find_all("li", {"class": "product-card-seller-info__spec-item atc-type-picanto"})
            for li in seller_details:
                distance_details = li.text.strip().replace("(", "").replace("miles", "").replace(")", "").split()
                distance = distance_details[-1]
                # when the distance of the seller isn't provided, the returned value will be "reviews" from the first li tag
                # list value as N/A to signify no exact distance data could be retrieved
                if "reviews" in distance:
                    distance = "N/A"
            product_details = [title, price, reg, body_type, mileage, engine_size, engine_power, gearbox, fuel_type, seller_name, distance, product_url]
            all_results.append(product_details)
        print(f'page no. {page} parsed')
        time.sleep(3)
    return all_results


def parse_results(url):
    """Parse webpage results using BeautifulSoup"""
    req = urlopen(url)
    page_html = req.read()
    req.close()
    soup = BeautifulSoup(page_html, "html.parser")
    return soup


if __name__ == '__main__':
    main()