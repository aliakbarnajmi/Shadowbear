import pandas
import datetime
import json
import requests
import time
import random


def find_iran_node():
    url = "https://check-host.net/nodes/hosts"
    js = json.loads(requests.get(url, headers={"Accept": "application/json"}).text)
    iran_nodes = []
    for key, value in js['nodes'].items():
        if "ir" in value.get("location"):
            iran_nodes.append(key)
    return iran_nodes  
    
def id_key_part(target, method, nodes):
    url = f"https://check-host.net/check-{method}?host={target}"
    for node in nodes:
        url += f"&node={node}"
    id_key_req = json.loads(requests.get(url, headers={"Accept": "application/json"}).text)
    # trigger // reached API limit
    if "request_id" not in id_key_req:
        return 0
    return id_key_req

def result_data_part(id_key):
	result_data_req = json.loads(requests.get(f"https://check-host.net/check-result/" + id_key["request_id"]).text)
	return result_data_req

def loading_process_part(index):
	animation_frames = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]
	index_frame = index % len(animation_frames)
	process_string = "{ info }" + " loading data from result data " + animation_frames[index_frame]
	return process_string

def ping_data_parser(result_data, data_frame_temp, id_key):
	for count, nod_location in enumerate(result_data, start=0):
		# id key data // api_data --> id_key_part()
		country = id_key["nodes"][nod_location][1]
		city    = id_key["nodes"][nod_location][2]
		if result_data[nod_location] != None:
			# result data // api_data --> result_data_part()
			data_in_result_data = result_data[nod_location][0]
			if data_in_result_data == None:
				data_frame_temp.loc[count] = [f"{country}, {city}", "no data", "no data", "no data"]
			if data_in_result_data != None:
				# result data // data_in_result_data
				Avg_time = round((data_in_result_data[0][1] + data_in_result_data[1][1] + data_in_result_data[2][1] + data_in_result_data[3][1]) * 1000 / 4, 1)
				code_1, code_2, code_3, code_4 = data_in_result_data[0][0], \
				                                 data_in_result_data[1][0], \
				                                 data_in_result_data[2][0], \
				                                 data_in_result_data[3][0]
				ip_address = data_in_result_data[0][2]
				data_frame_temp.loc[count] = [f"{country}, {city}", Avg_time, f"{code_1}/{code_2}/{code_3}/{code_4}", ip_address]
	# remove index // set index to ""
	data_frame_temp.index = [""] * len(data_frame_temp)
	return data_frame_temp

def ping_data_part(data_frame, id_key, index_count):
	# trigger // api_data --> id_key_part()
	if id_key == 0:
		return data_frame
		# datetime.datetime.now().strftime("%H:%M:%S") + " { error } inf: reached API limit, wait a minute."
	result_data = result_data_part(id_key)
	for nod_location in result_data:
		if result_data[nod_location] == None:
			# next frame // index_frame
			index_count += 1
			print(loading_process_part(index_count), end="\r", flush=True)
			return ping_data_part(data_frame, id_key, index_count)
	# return final data frame // data_frame
	return ping_data_parser(result_data, data_frame, id_key)

def ping_part(target):
    data_frame = pandas.DataFrame(columns=["location", "Latency", "code", "IP address"])
    pandas.set_option("display.width", 150)
    iran_nodes = find_iran_node()
    index_count = 0
    id_key = id_key_part(target, "ping", iran_nodes)
    print(f"Pingig\t{target}\tstarted at: ", datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    ping_data = ping_data_part(data_frame, id_key, index_count)
    if ping_data.empty:
        return False
    # print(ping_data)
    
    code_list = ping_data['code'].tolist()
    tmp = code_list[0]
    for i in range(1, len(code_list)):
        tmp += "/" + code_list[i]
    full_point = tmp.count("/") + 1
    point_quality = tmp.count("OK")
    quality_percent = int(point_quality / full_point * 100)
    # status_list = ["Clean", "Blocked", "Dirty"]
    if point_quality >= 15:
        status = "Clean"
    elif point_quality <= 1:
        status = "Blocked"
    else:
        status = "Dirty"
	# print(f"point_quality = {quality_percent}")
    # print("{ info } PING ended in:", datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    latency = int(ping_data.loc[:, 'Latency'].mean())
    if latency < 60:
        isIranIP = True
    else:
        isIranIP = False
    cols = ["IP", "DateTime", "Quality", "Status", "Check-host-Latency", "IranIP"]
    return f"{target},{int(time.time())},{quality_percent},{status},{latency},{isIranIP}"

def ping_multiple_ips(ips):
    error = 0
    all_data = []
    while len(ips) > 0:
        ip = ips.pop(0)
        data = ping_part(ip)
        if data:
            time.sleep(random.randint(100, 1000) / 1000)
            all_data.append(data)
        else:
            time.sleep(random.randint(2000, 5000) / 1000)
            print("reached API limit, wait a sec.")
            ips.append(ip)
            error += 1
        if error > 10:
            break
    df = pandas.DataFrame(all_data)
    print(df)
    return df

if __name__ == "__main__":
    # ping_multiple_ips(["188.245.241.232", "31.56.39.169"])
    ping_multiple_ips(["soft98ir-jamarnnews-mc.irangostarbike.ir"])
