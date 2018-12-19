import requests
from bs4 import BeautifulSoup
import pprint

# this has all of the events that we can use to grab all of the reults
base = "https://webpoint.usaweightlifting.org/"
meet_list = f"{base}wp15/Events2/Events.wp?evt_CategoryID=12"


# we need to fill the hidden form
form = {
    "evt_State": "CA",
    "evt_ActiveDateFrom": "1/01/2016",
    "evt_ActiveDateTo": "12/17/2018",
    "RF": "ST",
    "FRM": None,
    "evt_CategoryID": "12"
}

def get_local_event_list():
    """
    Get the links for all of the events in the given time period
    """
    response = requests.post(meet_list, form)
    soup = BeautifulSoup(response.content, features="html.parser")
    events = soup.findAll("a", {"class": "tinybutton"})
    links = ["{}{}".format(base, e["href"]) for e in events]
    return links


def get_event_results(target):
    # results are tagged with &isPopup=&Tab=Results
    response = requests.get(f"{target}&isPopup=&Tab=Results")
    return response.content

def get_event_date(target):
    response = requests.get(f"{target}&isPopup=&Tab=Results")
    soup = BeautifulSoup(response.content, features="html.parser")
    table = soup.find("table", {"class": "reportable"})


def parse_lifter(row):
    """
    Given something like the followig from beautiful soup

    <tr class="rowoff">
       <td> </td>
       <td valign="top"> Jeremy Winn</td>
       <td>Signal Hill, CA</td>
       <td>185</td>
    </tr>

    return a dict of {'name': 'Jeremy Winn', 'from': 'Signal Hill, CA', 'result': 185}
    """
    sepd = row.get_text('|', strip=True).split('|')
    return {
        'name': sepd[0],
        'from': sepd[1],
        'result': sepd[2]
    }


def parse_lifts(row):
    """
    Given a line like:

    'Weight Class:|69 Kg|Total:|123|Competition Weight:|68.2|Snatch 1:|53|Snatch 2:|-55|Snatch 3:|55|Best Snatch:|55|CleanJerk 1:|68|CleanJerk 2:|-71|CleanJerk 3:|-72|Best CleanJerk:|68'

    return a dictionary like

    {
    'weight_class': '69',
    'total': 123,
    'competition_weight': 68.2,
    'snatch1': 53,
    'snatch2': -55,
    'snatch3': 55,
    'best_snatch': 55,
    'cj1': 68,
    'cj2': -71,
    'cj3': -72,
    'best_cj': 68
    }

    """
    result = row.split('|')
    return {
        'weight_class': result[1],
        'total': result[3],
        'competition_weight': result[5],
        'snatch1': result[7],
        'snatch2': result[9],
        'snatch3': result[11],
        'best_snatch': result[13],
        'cj1': result[15],
        'cj2': result[17],
        'cj3': result[19],
        'best_cj': result[21]
    }



def parse(event_url, body):
    # format is a table with 2 rows devoted to a given athelete
    soup = BeautifulSoup(body, features="html.parser")
    table = soup.find("table", {"class": "list_table"})
    rows = table.find_all("tr")

    meet = {
        'event_url': event_url,
        'name': None,
        'results': []
    }

    lifter = None
    for ct, row in enumerate(rows):

        # assume that the first row is the title of the meet
        if ct == 0:
            name = row.find('td').get_text()
            meet['name'] = name

        # assume the second row is table info, we don't care about it
        # parse the lifts!
        elif ct > 1:
            # we have to get the lifter name and city in the row, then the
            # following row has the rest of the info for lifts
            # import pdb; pdb.set_trace()

            # rowon is a style for the lifter empty, name, home, result. These are TDs
            # smallinfo rowon the style for the lifts
            # titlerow is for the weightclass

            lifter_row = row.find('td', {'valign': 'top'})
            if lifter_row is not None:
                lifter = parse_lifter(row)

            lifts_or_header = row.get_text('|', strip=True)
            if "Weight Class" in lifts_or_header:
                lifts = parse_lifts(lifts_or_header)
                lifter['lifts'] = lifts
                meet['results'].append(lifter)
                lifter = None
    return meet

def main():
    event_links = get_local_event_list()
    for event in event_links[0:1]:
        #event_date = get_event_date(event)
        raw_results = get_event_results(event)
        parsed = parse(event, raw_results)
        pprint.pprint(parsed)


if __name__ == '__main__':
    main()
