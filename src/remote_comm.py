import requests as requests


COLOR_MAP = {
    "-1": "black",
    "0": "red",
    "1": "orange",
    "2": "gold",
    "3": "lime",
    "4": "green",
    "5": "cyan",
    "6": "blue",
    "7": "purple",
    "8": "fuchsia"
}


def sendScanToServer(scan):

    # json_data = {
    #     "data": [
    #         {"degrees": x, "distance": y/10, "color": COLOR_MAP[str(color)]}
    #         for x, y, color in scan
    #     ]
    # }

    # UpsertData("LiDAR", "LiDAR", json_data)
    json_data = {
        "data": []
    }

    for label, points in scan.items():
        color = COLOR_MAP.get(str(label), "unknown")
        data_entry = [
            {"degrees": x, "distance": y/15, "color": color}
            for x, y in points
        ]
        json_data["data"].extend(data_entry)

    # print(json_data)
    httpUpsertData("LiDAR", "LiDAR", json_data)


# =========================================================================
# Example Function to update a key/value pair in a database,
# or insert a new key/value pair if it doesn't already exist

def httpUpsertData(device_name, db_name, object):
    upsert_url = "http://localhost:3000/data/upsert-data"
    upsertDataPayload = {
        "meta_data": {
            "auth_token": "01",
            "sender": "Local"
        },
        "data": {
            "device_name": device_name,
            "db_name": db_name,
            "insert": object
        }
    }
    response = requests.post(upsert_url, json=upsertDataPayload)
    # Print the response
    # print(response.text)


def streamScan(scan):
    pass
