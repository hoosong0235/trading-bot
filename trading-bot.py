import requests
import json
import datetime
import time
import yaml
import statistics


# Open Config
with open('config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)

APP_KEY = _cfg['APP_KEY']
APP_SECRET = _cfg['APP_SECRET']
ACCESS_TOKEN = ""
CANO = _cfg['CANO']
ACNT_PRDT_CD = _cfg['ACNT_PRDT_CD']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
URL_BASE = _cfg['URL_BASE']
TIME_SLEEP = 0.5


# Send Message to Discord
def send_message(msg):
    print(msg)
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"}
    requests.post(DISCORD_WEBHOOK_URL, data={"content": f"** **"})
    time.sleep(TIME_SLEEP)
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    time.sleep(TIME_SLEEP)


# Hashkey
def hashkey(datas):
    headers = {
        'content-Type': 'application/json',
        'appKey': APP_KEY,
        'appSecret': APP_SECRET}
    body = datas
    PATH = "uapi/hashkey"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    HASH = res.json()["HASH"]

    return HASH


# Get Access Token
def get_access_token():
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET}
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    ACCESS_TOKEN = res.json()["access_token"]

    send_message(f"Get Access Token: OK")

    return ACCESS_TOKEN


# Revoke Access Token
def revoke_access_token():
    headers = {"content-type": "application/json"}
    body = {"appkey": APP_KEY,
            "appsecret": APP_SECRET,
            "token": ACCESS_TOKEN}
    PATH = "oauth2/revokeP"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))

    send_message(f"Revoke Access Token: OK")


# Inquire Price
def inquire_price(ISCD):
    headers = {
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "FHKST01010100",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": ISCD,
    }
    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.get(URL, headers=headers, params=params)
    OUTPUT = res.json()['output']
    PRPR = int(OUTPUT['stck_prpr'])

    return PRPR


# Inquire Daily Item Chart Price
def inquire_daily_itemchartprice(ISCD):
    DATE_1 = (datetime.date.today() -
              datetime.timedelta(days=29)).strftime("%Y%m%d")
    DATE_2 = (datetime.date.today() -
              datetime.timedelta(days=1)).strftime("%Y%m%d")
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "FHKST03010100",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": ISCD,
        "FID_INPUT_DATE_1": DATE_1,
        "FID_INPUT_DATE_2": DATE_2,
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "0",
    }
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.get(URL, headers=headers, params=params)
    OUTPUT = res.json()['output2']

    CLPR_LIST = []
    for day in OUTPUT:
        CLPR_LIST.append(int(day['stck_clpr']))

    send_message(f"Inquire Daily Item Chart Price: OK")

    return CLPR_LIST


# Calculate Mean and Standard Deviation
def calculate_mean_and_standard_deviation(CLPR_LIST):
    MEAN = int(statistics.mean(CLPR_LIST))
    STDDEV = int(statistics.stdev(CLPR_LIST))

    send_message(f"Calculate Mean and Standard Deviation: OK")

    return MEAN, STDDEV


# Main
try:
    IS_INITIALIZED = False

    while True:

        TIME_NOW = datetime.datetime.now()

        if not IS_INITIALIZED:

            IS_INITIALIZED = True
            ACCESS_TOKEN = get_access_token()

            ISCD_DICT = {"005930": (), "035420": (), "035720": ()}
            SEND_LIST = []

            for ISCD in ISCD_DICT.keys():
                CLPR_LIST = inquire_daily_itemchartprice(ISCD)
                MEAN, STDDEV = calculate_mean_and_standard_deviation(CLPR_LIST)
                ISCD_DICT[ISCD] = (MEAN, STDDEV)

            TIME_BEGIN = TIME_NOW.replace(
                hour=9, minute=0, second=0, microsecond=0)
            TIME_END = TIME_NOW.replace(
                hour=15, minute=0, second=0, microsecond=0)

        if TIME_NOW < TIME_END:

            for ISCD in ISCD_DICT.keys():

                if ISCD in SEND_LIST:
                    continue

                else:
                    PRHI = ISCD_DICT[ISCD][0] + 2 * ISCD_DICT[ISCD][1]
                    PRPR = inquire_price(ISCD)
                    PRLO = ISCD_DICT[ISCD][0] - 2 * ISCD_DICT[ISCD][1]

                    if (PRPR < PRLO):
                        SEND_LIST.append(ISCD)
                        send_message(
                            f"Trading Bot: {ISCD} PRPR({PRPR}₩) is lower than PRLO({PRLO}₩)")
                    if (PRPR > PRHI):
                        SEND_LIST.append(ISCD)
                        send_message(
                            f"Trading Bot: {ISCD} PRPR({PRPR}₩) is higher than PRHI({PRHI}₩)")

            if TIME_NOW.minute == 30 and TIME_NOW.second < 5:

                send_message("Trading Bot: OK")
                time.sleep(5)

    else:

        IS_INITIALIZED = False
        revoke_access_token()

        time.sleep((datetime.datetime.combine(TIME_NOW.date(
        ) + datetime.timedelta(days=1), datetime.time(9, 0)) - TIME_NOW).total_seconds())

except Exception as e:
    send_message(f"Exception: {e}")
