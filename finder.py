import requests
from bs4 import BeautifulSoup

# this has all of the events that we can use to grab all of the reults
meet_list = "https://webpoint.usaweightlifting.org/wp15/Events2/Events.wp?evt_CategoryID=12"

# we need to fill the hidden form
form = {
    "evt_State": "CA",
    "evt_ActiveDateFrom": "1/01/2016",
    "evt_ActiveDateTo": "12/17/2018",
    "RF": "ST",
    "FRM": None,
    "evt_CategoryID": "12"
}

def get_events():
    response = requests.post(meet_list, form)
    soup = BeautifulSoup(response.content, features="html.parser")
    events = soup.findAll("a", {"class": "tinybutton"})
    print(events)
    import pdb; pdb.set_trace()

if __name__ == '__main__':
    print(get_events())
