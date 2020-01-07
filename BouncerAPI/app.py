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


def post_request(service, command, payload):
    url = f"https://lalu.sirsi.net/lalu_ilsws/rest/{service}/{command}"
    response = requests.post(url, data=payload)
    return response


def login(username, password):
    service = "security"
    command = "loginUser"
    payload = {
        "login": username,
        "password": password,
        "clientID": "DS_CLIENT",
        "json": True,
    }
    r = post_request(service=service, command=command, payload=payload)
    return json.loads(r.content)["sessionToken"]


def lookup_patron(userid, token):
    service = "patron"
    command = "lookupPatronInfo"
    payload = {
        "userID": userid,
        "sessionToken": token,
        "clientID": "DS_CLIENT",
        "json": True,
        "includePatronInfo": True,
        "includePatronStatusInfo": True,
    }
    r = post_request(service=service, command=command, payload=payload)
    return r


def get_userinfo(token, userid):

    # This branch is for a complete miss.  Short-circuit.
    # The ID could not possibly match something in Sirsi.
    # Return a dict filled with default values, so the logger doesn't choke.
    if not (userid and len(userid) == 17):
        userinfo = dict()
        userinfo = add_missing_fields(userinfo)
        return userinfo

    response = lookup_patron(userid, token)
    userinfo = parse_response(response)

    # This branch is for a partial miss.
    # We got a response from Sirsi, but the response has a value that doesn't match anything in the enrichment dataset.
    # Either Sirsi gave us an "Unknown Dept" null response,
    # or Sirsi gave us a valid dept that happens to not be in the DEGREE_ATTRIBUTES enrichment dataset.
    # We'll fill in the missing values, so the logger doesn't choke.
    if userinfo["Curriculum Code"] not in DEGREE_ATTRIBUTES:
        userinfo = add_missing_fields(userinfo)
        return userinfo

    # This branch is for a complete hit.
    else:
        enrichment = DEGREE_ATTRIBUTES[userinfo["Curriculum Code"]]
        userinfo.update(enrichment)

        # There remains an edge case in the enrichment dataset.
        # Grad school & professional schools have no "College" assigned, so
        # we assign to them a generic "Graduate or Professional" value for College
        if not userinfo.get("College"):
            userinfo["College"] = "Graduate or Professional"

        return userinfo


def add_missing_fields(userinfo):
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
    # for missing key/values, add defaults
    for k, v in defaults.items():
        if k not in userinfo:
            userinfo[k] = v
    return userinfo


def parse_response(r):
    info = json.loads(r.text)
    # the following syntax saves so much space, that I'll risk the added complexity
    # info is {key1: {key2: value}, etc}
    # if key1 or key2 are missing, then it returns a default value
    # An example, key1 is "patronStatusInfo" and key2 is "datePrivilegeExpires"
    # The actual value returns if both keys exist, otherwise "1900-01-01" returns
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
    token = login(username, password)
    userid = request.args.get("id")
    userinfo = get_userinfo(token, userid)
    # we log a bunch of non-identifiable info
    log_access(userinfo)
    # but we only expose "expiration" to the outside world
    displayed_userinfo = {"expiration": userinfo["Expiration"]}
    return jsonify(displayed_userinfo)


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=8000)
