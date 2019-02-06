import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pprint
import sqlite3
from urllib.parse import urljoin

from parsita import TextParsers, reg, opt, Success, Failure

# this has all of the events that we can use to grab all of the reults
base = "https://webpoint.usaweightlifting.org/"

local_meets = f"{base}wp15/Events2/Events.wp?evt_CategoryID=12"
national_meets = f"{base}wp15/Events2/Events.wp?evt_CategoryID=13"

start = "1/01/2011"
end = "1/26/2015"
#end = "1/19/2019"

# we need to fill the hidden form
def local_form(state):
    return {
        "evt_State": state,
        "evt_ActiveDateFrom": start,
        "evt_ActiveDateTo": end,
        "RF": "ST",
        "FRM": None,
        "evt_CategoryID": "12",
    }


form_national = {
    "evt_State": None,
    "evt_ActiveDateFrom": start,
    "evt_ActiveDateTo": end,
    "RF": "ST",
    "FRM": None,
    "evt_CategoryID": "13",
}


def get_event_list(meet_list, form, state=None):
    """
    Get the links for all of the events in the given time period
    """
    response = requests.post(meet_list, form)
    soup = BeautifulSoup(response.content, features="html.parser")
    events = soup.findAll("a", {"class": "tinybutton"})
    links = [urljoin(base, e["href"]) for e in events]
    return links


def get_event_results(target):
    # results are tagged with &isPopup=&Tab=Results
    response = requests.get(f"{target}&isPopup=&Tab=Results")
    return response.content


def get_event_date(target):
    response = requests.get(target)
    soup = BeautifulSoup(response.content, features="html.parser")
    # let's just grab the first datetime with this. This will contain some trash
    raw_date = soup.find("td", {"valign": "top"}).get_text(strip=False)
    raw_date = raw_date.replace("\xa0", " ")
    raw_date = raw_date.split("(")[0]
    raw_date = raw_date.strip()

    # not all of the dates follow this format!
    # format things like Date/Time: Saturday, January 02, 2016 ', '12:00  PM - 2:00  PM)

    fmt_normal = "Date/Time: %A, %B %d, %Y"
    fmt_shorter = "Date/Time: %A, %b. %d, %Y"
    for fmtr in [fmt_normal, fmt_shorter]:
        try:
            return datetime.strptime(raw_date, fmtr).date()
        except ValueError:
            pass

    # if this hasn't worked, we need to parse a date like
    fmt = "Date/Time: %m/%d/%Y "
    raw_date = raw_date.split("-")[0]
    return datetime.strptime(raw_date, fmt).date()


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
    sepd = row.get_text("|", strip=True).split("|")
    try:
        return {"name": sepd[0], "from": sepd[1]}
    except IndexError:
        print(f"Failure with row: {row}\n {sepd}")
        raise



class UsawParser(TextParsers, whitespace=None):
    floatP = reg(r'[+-]?[0-9]*\.?[0-9]+')

    # actual fields
    WeightClass = "Weight Class:|" >> reg(r'[0-9]+[-+]?') << ' Kg|'
    Total = "Total:|" >> floatP << "|" > float
    CompetitionWeight = "Competition Weight:|" >> floatP << '|' > float
    snatches = reg(r'Snatch [1-3]:|') >> floatP
    Sn1 = "Snatch 1:|" >> opt(floatP << '|' > float)
    Sn2 = "Snatch 2:|" >> opt(floatP << '|' > float)
    Sn3 = "Snatch 3:|" >> opt(floatP << '|' > float)
    BestSn = "Best Snatch:|" >> floatP << '|' > float
    Cj1 = "CleanJerk 1:|" >> opt(floatP << '|' > float)
    Cj2 = "CleanJerk 2:|" >> opt(floatP << '|' > float)
    Cj3 = "CleanJerk 3:|" >> opt(floatP << '|' > float)
    BestCj = "Best CleanJerk:|" >> floatP > float
    value = WeightClass & Total & CompetitionWeight & Sn1 & Sn2 & Sn3 & BestSn & Cj1 & Cj2 & Cj3 & BestCj


def parse_lifts(row):
    """
    Given a line like:

    'Weight Class:|69 Kg|Total:|123|Competition Weight:|68.2|Snatch 1:|53|Snatch 2:|-55|Snatch 3:|55|Best Snatch:|55|CleanJerk 1:|68|CleanJerk 2:|-71|CleanJerk 3:|-72|Best CleanJerk:|68'

    return a dictionary like:
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
    # this is the original row
    # 'Weight Class:|58 Kg|Total:|217|Competition Weight:|106.5|Snatch 1:|Snatch 2:|Snatch 3:|Best Snatch:|92.5|CleanJerk 1:|CleanJerk 2:|CleanJerk 3:|Best CleanJerk:|125'
    def get_value(lst, idx):
        try:
            return lst[idx][0]
        except IndexError:
            return 0

    parsed = UsawParser.value.parse(row)
    if isinstance(parsed, Success):
        value = parsed.value
        return {
            "weight_class": value[0],
            "total": value[1],
            "competition_weight": value[2],
            "sn1": get_value(value, 3),
            "sn2": get_value(value, 4),
            "sn3": get_value(value, 5),
            "best_sn": value[6],
            "cj1": get_value(value, 7),
            "cj2": get_value(value, 8),
            "cj3": get_value(value, 9),
            "best_cj": value[10],
        }
    else:
        print("Bad row: {}", parsed)

def parse(event_url, body):
    # format is a table with 2 rows devoted to a given athelete
    soup = BeautifulSoup(body, features="html.parser")
    table = soup.find("table", {"class": "list_table"})
    rows = table.find_all("tr")

    meet = {"event_url": event_url, "name": None, "results": []}

    lifter = None
    meet["name"] = soup.find("tr", {"class": "pagetitlerow"}).get_text(strip=True)
    for ct, row in enumerate(rows):

        # assume that the first row is the title of the meet
        if ct == 0:
            pass

        # assume the second row is table info, we don't care about it
        # parse the lifts!
        elif ct > 1:
            # we have to get the lifter name and city in the row, then the
            # following row has the rest of the info for lifts
            # rowon is a style for the lifter empty, name, home, result. These are TDs
            # smallinfo rowon the style for the lifts
            # titlerow is for the weightclass

            lifter_row = row.find("td", {"valign": "top"})
            if lifter_row is not None:
                lifter = parse_lifter(row)

            lifts_or_header = row.get_text("|", strip=True)
            if "Weight Class:" in lifts_or_header:
                lifts = parse_lifts(lifts_or_header)
                lifter["lifts"] = lifts
                # we could fail parsing, if so, don't add
                if lifts is not None:
                    meet["results"].append(lifter)
                lifter = None
    return meet


_schema = """
CREATE TABLE IF NOT EXISTS results
                 (date text
                 , meet_name text
                 , lifter text
                 , weight_class real
                 , competition_weight real
                 , hometown text
                 , cj1 real
                 , cj2 real
                 , cj3 real
                 , sn1 real
                 , sn2 real
                 , sn3 real
                 , total real
                 , best_snatch real
                 , best_cleanjerk real
                 , url text
                , UNIQUE (date, meet_name, lifter, weight_class, url) ON CONFLICT REPLACE);
"""

def build_db():
    conn = sqlite3.connect("lifts2.db")
    c = conn.cursor()
    c.execute(_schema)
    conn.commit()
    return conn


class Row:
    def __init__(
        self,
        date,
        event_name,
        lifter_name,
        weight_class,
        competition_weight,
        home,
        cj1,
        cj2,
        cj3,
        sn1,
        sn2,
        sn3,
        total,
        best_snatch,
        best_cleanjerk,
        event_url,
    ):
        self.date = date
        self.event_name = event_name
        self.lifter_name = lifter_name
        self.weight_class = weight_class
        self.competition_weight = competition_weight
        self.home = home
        self.cj1 = cj1
        self.cj2 = cj2
        self.cj3 = cj3
        self.sn1 = sn1
        self.sn2 = sn2
        self.sn3 = sn3
        self.total = total
        self.best_snatch = best_snatch
        self.best_cleanjerk = best_cleanjerk
        self.event_url = event_url

    def to_tuple(self):
        # this needs to match the schema when the DB is built!
        return (
            self.date,
            self.event_name,
            self.lifter_name,
            self.weight_class,
            self.competition_weight,
            self.home,
            self.cj1,
            self.cj2,
            self.cj3,
            self.sn1,
            self.sn2,
            self.sn3,
            self.total,
            self.best_snatch,
            self.best_cleanjerk,
            self.event_url,
        )


def insert_meet(conn, meet):
    c = conn.cursor()
    rows = []
    for lifter in meet["results"]:
        lifts = lifter["lifts"]
        row = Row(
            meet["date"],
            meet["name"],
            lifter["name"],
            lifts["weight_class"],
            lifts["competition_weight"],
            lifter["from"],
            lifts["cj1"],
            lifts["cj2"],
            lifts["cj3"],
            lifts["sn1"],
            lifts["sn2"],
            lifts["sn3"],
            lifts["total"],
            lifts["best_sn"],
            lifts["best_cj"],
            meet["event_url"],
        )
        rows.append(row.to_tuple())

    print(rows)
    c.executemany(
        "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
    )
    conn.commit()


def exists(conn, event_url):
    c = conn.cursor()
    res = c.execute("SELECT EXISTS (SELECT 1 FROM results WHERE url=?)", (event_url,))
    return res.fetchone() == (1,)


# Get all of the states
states = {
    "AK": "Alaska",
    "AL": "Alabama",
    "AR": "Arkansas",
    "AS": "American Samoa",
    "AZ": "Arizona",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DC": "District of Columbia",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "GU": "Guam",
    "HI": "Hawaii",
    "IA": "Iowa",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MA": "Massachusetts",
    "MD": "Maryland",
    "ME": "Maine",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MO": "Missouri",
    "MP": "Northern Mariana Islands",
    "MS": "Mississippi",
    "MT": "Montana",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "NE": "Nebraska",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NV": "Nevada",
    "NY": "New York",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "PR": "Puerto Rico",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VA": "Virginia",
    "VI": "Virgin Islands",
    "VT": "Vermont",
    "WA": "Washington",
    "WI": "Wisconsin",
    "WV": "West Virginia",
    "WY": "Wyoming",
}


def main():
    conn = build_db()
    event_links = []
    for state in states.keys():
        event_links.extend(get_event_list(local_meets, local_form(state)))
    event_links.extend(get_event_list(national_meets, form_national))
    for event in event_links:
        print(f"Event url: {event}")
        if exists(conn, event):
            print("already in DB")
        else:
            event_date = get_event_date(event)
            raw_results = get_event_results(event)
            parsed = parse(event, raw_results)
            parsed["date"] = event_date
            insert_meet(conn, parsed)


if __name__ == "__main__":
    main()
