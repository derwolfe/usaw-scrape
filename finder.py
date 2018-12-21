import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pprint
import sqlite3
from urllib.parse import urljoin


# this has all of the events that we can use to grab all of the reults
base = "https://webpoint.usaweightlifting.org/"

local_meets = f"{base}wp15/Events2/Events.wp?evt_CategoryID=12"
national_meets = f"{base}wp15/Events2/Events.wp?evt_CategoryID=13"

# we need to fill the hidden form
form_local = {
    "evt_State": "CA",
    "evt_ActiveDateFrom": "1/01/2016",
    "evt_ActiveDateTo": "12/17/2018",
    "RF": "ST",
    "FRM": None,
    "evt_CategoryID": "12"
}

form_national = {
    "evt_State": None,
    "evt_ActiveDateFrom": "1/01/2016",
    "evt_ActiveDateTo": "12/17/2018",
    "RF": "ST",
    "FRM": None,
    "evt_CategoryID": "13"
}


def get_event_list(meet_list, form):
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
    raw_date = soup.find('td', {'valign': 'top'}).get_text(strip=False)
    raw_date = raw_date.replace(u'\xa0', u' ')
    raw_date = raw_date.split('(')[0]
    raw_date = raw_date.strip()

    # not all of the dates follow this format!
    # format things like Date/Time: Saturday, January 02, 2016 ', '12:00  PM - 2:00  PM)

    fmt_normal = 'Date/Time: %A, %B %d, %Y'
    fmt_shorter = 'Date/Time: %A, %b. %d, %Y'
    for fmtr in [fmt_normal, fmt_shorter]:
        try:
            return datetime.strptime(raw_date, fmtr).date()
        except ValueError:
            pass

    # if this hasn't worked, we need to parse a date like
    fmt = 'Date/Time: %m/%d/%Y '
    raw_date = raw_date.split('-')[0]
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
    sepd = row.get_text('|', strip=True).split('|')
    try:
        return {
            'name': sepd[0],
            'from': sepd[1],
        }
    except IndexError:
        print(f"Failure with row: {row}\n {sepd}")
        raise



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
    try:
        return {
            'weight_class': result[1],
            'total': result[3],
            'competition_weight': result[5],
            'sn1': result[7],
            'sn2': result[9],
            'sn3': result[11],
            'best_snatch': result[13],
            'cj1': result[15],
            'cj2': result[17],
            'cj3': result[19],
            'best_cj': result[21]
        }
    except IndexError:
        print(f"Bad row: {row}")


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
    meet['name'] = soup.find('tr', {'class': 'pagetitlerow'}).get_text(strip=True)
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

            lifter_row = row.find('td', {'valign': 'top'})
            if lifter_row is not None:
                lifter = parse_lifter(row)

            lifts_or_header = row.get_text('|', strip=True)
            if "Weight Class" in lifts_or_header:
                lifts = parse_lifts(lifts_or_header)
                lifter['lifts'] = lifts
                # we could fail parsing, if so, don't add
                if lifts is not None:
                    meet['results'].append(lifter)
                lifter = None
    return meet


def build_db():
    conn = sqlite3.connect('lifts.db')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS results
                 (date text, meet_name text, lifter text, weight_class real, hometown text, cj1 real, cj2 real, cj3 real, sn1 real, sn2 real, sn3 real, total real, url text)""")
    conn.commit()
    return conn

def insert_meet(conn, meet):
    c = conn.cursor()
    rows = []
    for lifter in meet['results']:
        lifts = lifter['lifts']
        rows.append(
            (
                meet['date'],
                meet['name'],
                lifter['name'],
                lifts['weight_class'],
                lifter['from'],
                lifts['cj1'],
                lifts['cj2'],
                lifts['cj3'],
                lifts['sn1'],
                lifts['sn2'],
                lifts['sn3'],
                lifts['total'],
                meet['event_url'],
            )
        )

    c.executemany("INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()

def exists(conn, event_url):
    c = conn.cursor()
    res = c.execute("SELECT EXISTS (SELECT 1 FROM results WHERE url=?)", (event_url,))
    return res.fetchone() == (1,)

def main():
    conn = build_db()
    event_links = get_event_list(local_meets, form_local)
    event_links.extend(get_event_list(national_meets, form_national))
    for event in event_links:
        print(f'Event url: {event}')
        if exists(conn, event):
            print('already in DB')
        else:
            event_date = get_event_date(event)
            raw_results = get_event_results(event)
            parsed = parse(event, raw_results)
            parsed['date'] = event_date
            insert_meet(conn, parsed)


if __name__ == '__main__':
    main()
