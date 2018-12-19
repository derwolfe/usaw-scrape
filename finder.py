import requests
from bs4 import BeautifulSoup
import pprint

# this has all of the events that we can use to grab all of the reults
base = "https://webpoint.usaweightlifting.org/"
meet_list = f"{base}/wp15/Events2/Events.wp?evt_CategoryID=12"


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
    links = ["{}/{}".format(base, e["href"]) for e in events]
    return links


def get_event(target):
    # results are tagged with &isPopup=&Tab=Results
    response = requests.get(f"{target}&isPopup=&Tab=Results")
    return response.content


def parse(body):
    # format is a table with 2 rows devoted to a given athelete
    soup = BeautifulSoup(body, features="html.parser")
    table = soup.find("table", {"class": "list_table"})
    rows = table.find_all("td")

    rownum = 1
    import pdb; pdb.set_trace()
    for row in rows:

        # assume that the first row is the title of the meet
        if rownum == 1:
            continue

        # assume the second row is table info, we don't care about it
        elif rownum == 2:
            continue

        else:
            pass
        # let's bump this
        rownum =+ 1

    # pagetitlerow = Meetname
    # first row is the athelete name
    # second row is the result from the meet
    # <table cellpadding="1" class="list_table">
    # <tr class="pagetitlerow"><td colspan="4"><b>2016 SENSE Gym Weigthlifting Meet #1</b></td></tr>
    # <tr class="headerrow"><th> </th><th>Participant</th><th>Hometown</th><th>Result</th></tr>
    # <tr class="titlerow"><td colspan="4">63 Kg</td></tr>
    # <tr class="rowon">
    # <td> </td>
    # <td valign="top"> Jenny Ting</td>
    # <td>Long Beach, CA</td>
    # <td>147</td>
    # </tr>
    # <tr class="smallinfo rowon"><td> </td><td colspan="3"><b>Weight Class:</b> 63 Kg   <b>Total:</b> 147   <br/><b>Competition Weight:</b> 60   <b>Snatch 1:</b> 60   <b>Snatch 2:</b> 62   <b>Snatch 3:</b> 65   <b>Best Snatch:</b> 65   <b>CleanJerk 1:</b> 78   <b>CleanJerk 2:</b> 82   <b>CleanJerk 3:</b> -85   <b>Best CleanJerk:</b> 82   </td></tr>
    # <tr class="rowoff">
    # <td> </td>
    # <td valign="top"> Julie Quach</td>
    # <td>Garden Grove, CA</td>
    # <td>0</td>
    # </tr>
    # <tr class="smallinfo rowoff"><td> </td><td colspan="3"><b>Weight Class:</b> 63 Kg   <b>Total:</b> 0   <br/><b>Competition Weight:</b> 62.9   <b>Snatch 1:</b> -58   <b>Snatch 2:</b> -60   <b>Snatch 3:</b> -60   <b>Best Snatch:</b> 0   <b>CleanJerk 1:</b> -70   <b>CleanJerk 2:</b> 70   <b>CleanJerk 3:</b> 74   <b>Best CleanJerk:</b> 74   </td></tr>
    import pdb; pdb.set_trace()


def main():
    event_links = get_local_event_list()
    for event in event_links[0:1]:
        raw_results = get_event(event)
        parsed = parse(raw_results)


if __name__ == '__main__':
    main()
