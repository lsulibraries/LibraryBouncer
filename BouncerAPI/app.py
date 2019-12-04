#! usr/env/python3

import json
import logging
from datetime import datetime, timedelta

from flask import Flask, json, request, render_template, jsonify
import requests


application = Flask(__name__)


logging.basicConfig(
    filename="access_stats.txt",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    format="%(asctime)s;%(message)s",
)


with open('DegreeAttributes.json', 'r') as f:
    DEGREE_ATTRIBUTES = json.load(f)


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
    endpoint = pick_an_endpoint(userid, session_token)
    if not endpoint:
        enriched = {
            "College": "Unknown College",
            "Department": "Unknown Dept",
            "CIP Codes": "Unknown CIP Code",
            "Curriculum/Major": "Unknown Major",
            "Curriculum Code": "Unknown Curriculum Code",
            "Degree": "Unknown Degree",
            "Expiration": "1900-01-01",
            "user": "Unknown User",
        }
        log_access(enriched)
        return enriched
    response = session.post(endpoint)
    parsed = parse_response(response)
    enriched = enrich(parsed)
    log_access(enriched)
    return enriched


def pick_an_endpoint(userid, session_token):
    if userid and len(userid) == 17:
        endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/patron/lookupPatronInfo?clientID=DS_CLIENT&sessionToken={session_token}&userID={userid}&includePatronStatusInfo=True&includePatronInfo=True&json=True"
    else:
        endpoint = None
    return endpoint


def parse_response(r):
    info = json.loads(r.text)
    # the first .get() returns empty dict if key not found
    # the second .get() returns descriptive text for each missing type
    exp = info.get("patronStatusInfo", dict()).get("datePrivilegeExpires", "1900-01-01")
    dept = info.get("patronInfo", dict()).get("department", "Unknown Dept")
    user = info.get("patronInfo", dict()).get("displayName", "Unknown User")
    return {"Expiration": exp, "Curriculum Code": dept, "user": user}


def enrich(parsed):
    additional = DEGREE_ATTRIBUTES.get(parsed['Curriculum Code'])
    if additional:
        parsed.update(additional)
        # grad school & professional schools have no "College" in the reference DegreeAttributes.json
        # we give them a generic "Graduate or Professional" value for College
        if "College" not in parsed:
            parsed["College"] = "Graduate or Professional"
        return parsed
    else:
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
            if k not in parsed:
                parsed[k] = v
        return parsed


def log_access(parsed):
    if is_repeat(parsed):
        return
    exp = datetime.strptime(parsed["Expiration"], "%Y-%m-%d")
    now = datetime.now()
    dept = parsed.get("Department", "Unknown Dept")
    college = parsed.get('College', 'Unknown College')
    cip_codes = parsed.get('CIP Codes', 'Unknown CIP Code')
    curr_maj = parsed.get('Curriculum/Major', 'Unknown Major')
    curr_code = parsed.get('Curriculum Code', "Unknown Curriculum Code")
    degree = parsed.get('Degree', "Unknown Degree")
    if now > exp:
        logging.info(f"Denied;{college};{dept};{degree};{curr_maj};{cip_codes};{curr_code}")
    else:
        logging.info(f"Allowed;{college};{dept};{degree};{curr_maj};{cip_codes};{curr_code}")


recent_hits = list()


def is_repeat(parsed):
    is_match = False
    parsed["now"] = datetime.now()
    global recent_hits
    olds = [
        i
        for i in recent_hits
        if i.get("now") + timedelta(minutes=15) < datetime.now()
    ]
    for i in olds:
        recent_hits.remove(i)
    for i in recent_hits:
        if (i["user"], i["Curriculum Code"]) == (parsed["user"], parsed["Curriculum Code"]):
            is_match = True
            break
    recent_hits.append(parsed)
    return is_match


@application.route("/")
def index():
    username, password = parse_secrets()
    session, session_token = login(username, password)
    userid = request.args.get("id")
    userinfo = get_userinfo(session, session_token, userid)
    # To defend against scraping from a 3rd party, we only expose "expiration" to the outside world. 
    displayed_userinfo = {"expiration": userinfo["Expiration"]}
    return jsonify(displayed_userinfo)


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=8000)
