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
        return {"user": "Unknown user", "expiration": "1900-01-01"}
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
        # if userid isn't an 89 number or a 17-digit account number
        endpoint = None
    return endpoint


def parse_response(r):
    try:
        expiration = json.loads(r.text)["patronStatusInfo"]["datePrivilegeExpires"]
    except KeyError:
        expiration = "1900-01-01"
    try:
        user = json.loads(r.text)["patronInfo"]["displayName"]
    except KeyError:
        user = "Unknown user"
    return {"user": user, "expiration": expiration}


def log_access(parsed):
    user_exp = datetime.strptime(parsed["expiration"], "%Y-%m-%d")
    now = datetime.now()
    if now > user_exp:
        logging.info("Denied")
    else:
        logging.info("Allowed")


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
        lines = [line for line in f.read().split('\n') if line]
    stats = []
    for line in lines:
        t, s = line.split(" ----- ")
        stats.append({"time": t, "success": s})
    return jsonify(stats)


if __name__ == "__main__":
    application.run(host="127.0.0.1", port=8000)
