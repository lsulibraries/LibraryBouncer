#! usr/env/python3

import logging
from datetime import datetime

from flask import Flask, json, request, render_template, jsonify
import requests

application = Flask(__name__)

logging.basicConfig(
    filename="access_stats.txt",
    level=logging.INFO,
    format="%(asctime)s ----- %(message)s",
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
    endpoint = pick_an_endpoint(userid, session_token)
    if not endpoint:
        parsed = {
            "user": "Unknown User",
            "expiration": "1900-01-01",
            "department": "Unknown Dept",
        }
        log_access(parsed)
        return parsed
    response = session.post(endpoint)
    parsed = parse_response(response)
    log_access(parsed)
    return parsed


def pick_an_endpoint(userid, session_token):
    if not userid:
        endpoint = None
    elif len(userid) == 17:
        endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/patron/lookupPatronInfo?clientID=DS_CLIENT&sessionToken={session_token}&userID={userid}&includePatronStatusInfo=True&includePatronInfo=True&json=True"
    elif len(userid) == 9 and userid[:2] == "89":
        endpoint = f"https://lalu.sirsi.net/lalu_ilsws/rest/patron/lookupPatronInfo?clientID=DS_CLIENT&sessionToken={session_token}&alternateID={userid}&includePatronStatusInfo=True&includePatronInfo=True&json=True"
    else:
        # if userid is neither an 89 number nor a 17-digit account number
        endpoint = None
    return endpoint


def parse_response(r):
    info = json.loads(r.text)
    # first .get() returns empty dict if key not found
    # second .get() returns descriptive text for each missing type
    exp = info.get("patronStatusInfo", dict()).get(
        "datePrivilegeExpires", "Unknown Dept"
    )
    user = info.get("patronInfo", dict()).get("displayName", "Unknown User")
    dept = info.get("patronInfo", dict()).get("department", "1900-01-01")
    return {"user": user, "expiration": exp, "department": dept}


def log_access(parsed):
    exp = datetime.strptime(parsed["expiration"], "%Y-%m-%d")
    now = datetime.now()
    dept = parsed["department"]
    if now > exp:
        logging.info(f"Denied ----- {dept}")
    else:
        logging.info(f"Allowed ----- {dept}")


@application.route("/")
def index():
    username, password = parse_secrets()
    session, session_token = login(username, password)
    userid = request.args.get("id")
    userinfo = get_userinfo(session, session_token, userid)
    return jsonify(userinfo)


@application.route("/stats/")
def stats():
    with open("access_stats.txt", "r") as f:
        lines = [line for line in f.read().split("\n") if line]
    stats = []
    for line in lines:
        t, s, d = line.split(" ----- ")
        stats.append({"time": t, "success": s, "department": d})
    return jsonify(stats)


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=8000)
