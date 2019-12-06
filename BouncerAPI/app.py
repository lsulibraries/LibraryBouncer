#! usr/env/python3

import logging
from datetime import datetime, timedelta

import requests
from flask import Flask, json, request, jsonify


RECENTS = list()
with open("DegreeAttributes.json", "r") as f:
    DEGREE_ATTRIBUTES = json.load(f)


application = Flask(__name__)


logging.basicConfig(
    filename="access_stats.txt",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    format="%(asctime)s;%(message)s",
)


def parse_secrets():
    with open("user_pass.json", "r") as f:
        info = json.load(f)
    return info["user"], info["password"]


def login(username, password):
    endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/security/loginUser?clientID=DS_CLIENT&login={username}&password={password}&json=True"
    s = requests.session()
    r = s.post(endpoint)
    return s, json.loads(r.text)["sessionToken"]


def get_userinfo(session, session_token, userid):
    if not (userid and len(userid) == 17):
        """
        This branch is for a complete miss.
        The ID could not possibly match something in Sirsi.
        We'll create a dict filled with default fields, so the logger doesn't choke.
        """
        userinfo = dict()
        userinfo = selectively_update(userinfo)
        return userinfo

    endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/patron/lookupPatronInfo?clientID=DS_CLIENT&sessionToken={session_token}&userID={userid}&includePatronStatusInfo=True&includePatronInfo=True&json=True"
    response = session.post(endpoint)
    userinfo = parse_response(response)

    if userinfo["Curriculum Code"] not in DEGREE_ATTRIBUTES:
        """
        This branch is for a partial miss.
        We got some response from Sirsi, but the response has a value that doesn't match anything in the enrichment dataset.
        Either Sirsi gave us an "Unknown Dept" null response,
        or Sirsi gave us a valid dept that happends to not be in the DEGREE_ATTRIBUTES enrichment dataset.
        We'll fill in the missing fields, so the logger doesn't choke.
        """
        userinfo = selectively_update(userinfo)
        return userinfo

    else:
        additional = DEGREE_ATTRIBUTES[userinfo["Curriculum Code"]]
        userinfo.update(additional)
        if not userinfo.get( "College"):
            # This fixes an edge case in the enrichment dataset.
            # Grad school & professional schools have no "College" assigned, so
            # we assign to them a generic "Graduate or Professional" value for College
            userinfo["College"] = "Graduate or Professional"
        return userinfo


def selectively_update(userinfo):
    defaults = {
        "College": "Unknown College",
        "Department": "Unknown Dept",
        "CIP Codes": "Unknown CIP Code",
        "Curriculum/Major": "Unknown Major",
        "Curriculum Code": "Unknown Curriculum Code",
        "Degree": "Unknown Degree",
        "Expiration": "1900-01-01",
        "user": "Unknown User",
    }
    for k, v in defaults.items():
        if k not in userinfo:
            userinfo[k] = v
    return userinfo


def parse_response(r):
    info = json.loads(r.text)
    # the first .get() returns empty dict if key not found
    # the second .get() returns descriptive text for each missing type
    exp = info.get("patronStatusInfo", dict()).get("datePrivilegeExpires", "1900-01-01")
    dept = info.get("patronInfo", dict()).get("department", "Unknown Dept")
    user = info.get("patronInfo", dict()).get("displayName", "Unknown User")
    return {"Expiration": exp, "Curriculum Code": dept, "user": user}


def log_access(userinfo):
    if is_repeat(userinfo):
        return
    exp = datetime.strptime(userinfo["Expiration"], "%Y-%m-%d")
    now = datetime.now()
    dept = userinfo.get("Department", "Unknown Dept")
    college = userinfo.get("College", "Unknown College")
    cip_codes = userinfo.get("CIP Codes", "Unknown CIP Code")
    curr_maj = userinfo.get("Curriculum/Major", "Unknown Major")
    curr_code = userinfo.get("Curriculum Code", "Unknown Curriculum Code")
    degree = userinfo.get("Degree", "Unknown Degree")
    if now > exp:
        logging.info(
            f"Denied;{college};{dept};{degree};{curr_maj};{cip_codes};{curr_code}"
        )
    else:
        logging.info(
            f"Allowed;{college};{dept};{degree};{curr_maj};{cip_codes};{curr_code}"
        )


def is_repeat(userinfo):
    is_match = False
    userinfo["now"] = datetime.now()
    global RECENTS
    olds = [i for i in RECENTS if i.get("now") + timedelta(minutes=15) < datetime.now()]
    for i in olds:
        RECENTS.remove(i)
    for i in RECENTS:
        if (i["user"], i["Curriculum Code"]) == (
            userinfo["user"],
            userinfo["Curriculum Code"],
        ):
            is_match = True
            break
    RECENTS.append(userinfo)
    return is_match


@application.route("/")
def index():
    username, password = parse_secrets()
    session, session_token = login(username, password)
    userid = request.args.get("id")
    userinfo = get_userinfo(session, session_token, userid)
    # We log a decent amount of non-identifiable info
    log_access(userinfo)
    # But to defend against scraping from a 3rd party, we only expose "expiration" to the outside world.
    displayed_userinfo = {"expiration": userinfo["Expiration"]}
    return jsonify(displayed_userinfo)


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=8000)
