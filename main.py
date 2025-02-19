# We have Three Stage Configs:
# 1 - raw :         collect configs - rename configs - splitted by country
# 2 - active:       test config with litespeedtest and make sure that config are working properly
# 3 - check-host    check ip of active configs that is not blocked in iran

import json
import os
import socket
import asyncio
import time
import base64
import subprocess
import time
from datetime import datetime
from zipfile import ZipFile
from urllib.request import urlopen
import re
from urllib.parse import unquote
from check_host import ping_multiple_ips, ping_part
import random
import pandas as pd
from math import ceil

try:
    from tqdm import tqdm
    import requests
    import geoip2.database
except:
    print("installing packages : tqdm requests")
    subprocess.run("pip install --trusted-host https://pypi.tuna.tsinghua.edu.cn/simple/ tqdm requests geoip2", text=True, shell=True, capture_output=True)
    from tqdm import tqdm
    import requests
    import geoip2.database

PING_TEST_PATH = "ping_test.sh"
TEMP_PATH = "temp"
GEOLITE_CITY_PATH = f"{TEMP_PATH}/GeoLite2-City.mmdb"
GEOLITE_COUNTRY_PATH = f"{TEMP_PATH}/GeoLite2-Country.mmdb"
GEOLITE_ASN_PATH = f"{TEMP_PATH}/GeoLite2-ASN.mmdb"
IRAN_ASN_PATH = f"{TEMP_PATH}/IranASN.mmdb"
SPEEDTEST_LOG_PATH = f"{TEMP_PATH}/speedtest.log"

RAW_CONFIGS_PATH = "subs/raw"
RAW_CONFIGS_PROVIDER_PATH = f"{RAW_CONFIGS_PATH}/providers"
RAW_CONFIGS_COUNTRY_PATH = f"{RAW_CONFIGS_PATH}/countries"

ACTIVE_CONFIGS_PATH = "subs/active"
ACTIVE_CONFIGS_COUNTRY_PATH = f"{ACTIVE_CONFIGS_PATH}/countries"
ACTIVE_CONFIGS_RESULT_PATH = f"{ACTIVE_CONFIGS_PATH}/results"


CHECKHOST_CONFIGS_PATH = "subs/check_host"
CHECKHOST_CONFIGS_COUNTRY_PATH = f"{CHECKHOST_CONFIGS_PATH}/countries"
CHECKHOST_CONFIGS_RESULT_PATH = f"{CHECKHOST_CONFIGS_PATH}/results"

JOSN_OUTPUT_PATH = "output.json"
NOW = datetime.now().strftime("%Y.%m.%d-%H.%M.%S")

# ---------------           Setup           ------------------

def find_asn():
    asn_reader = geoip2.database.Reader(GEOLITE_ASN_PATH)
    iran_asn_reader = geoip2.database.Reader(IRAN_ASN_PATH)
    def getIP():
        d = str(urlopen('http://checkip.dyndns.com/')
                .read())

        return re.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').search(d).group(1)

    def find_asn_from_ip(ip):
        try:
            return asn_reader.asn(ip).autonomous_system_organization
        except:
            return "Unkown"

    def find_asn_iran_from_ip(ip):
        try:
            return iran_asn_reader.asn(ip).autonomous_system_organization
        except:
            return "Unkown"

    def map_asn(asn):
        asn_map_list = {
            "Aria Shatel PJSC": "SHT",
            "Iran Telecommunication Company PJS": "MKH",
            "Mobile Communication Company of Iran PLC": "MCI",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "": "",
            "Unkown": "Unkown",
        }
        for key, value in asn_map_list.items():
            if asn in key:
                return value
            

    ip_address = getIP()
    asn == "Unkown"
    if ip_address.replace(".", "").isdigit():
        asn = find_asn_from_ip()
        if asn == "Unkown":
            asn = find_asn_iran_from_ip(ip_address)
    
    return asn, map_asn(asn)

def setup_env():
    if not os.path.isdir(TEMP_PATH):
        os.mkdir(TEMP_PATH)
    if not os.path.isfile(GEOLITE_CITY_PATH):
        download("https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb", GEOLITE_CITY_PATH)
    if not os.path.isfile(GEOLITE_COUNTRY_PATH):
        download("https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb", GEOLITE_COUNTRY_PATH)
    if not os.path.isfile(GEOLITE_ASN_PATH):
        download("https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-ASN.mmdb", GEOLITE_ASN_PATH)
    if not os.path.isfile(IRAN_ASN_PATH):
        download("https://github.com/hsmamir/iran_asn_mmdb/raw/refs/heads/main/ir_asn.mmdb", IRAN_ASN_PATH)
    
    if not os.path.isdir("subs"):
        os.mkdir("subs")
    
    if not os.path.isdir(RAW_CONFIGS_PATH):
        os.mkdir(RAW_CONFIGS_PATH)
    if not os.path.isdir(RAW_CONFIGS_PROVIDER_PATH):
        os.mkdir(RAW_CONFIGS_PROVIDER_PATH)
    if not os.path.isdir(RAW_CONFIGS_COUNTRY_PATH):
        os.mkdir(RAW_CONFIGS_COUNTRY_PATH)
    
    if not os.path.isdir(ACTIVE_CONFIGS_PATH):
        os.mkdir(ACTIVE_CONFIGS_PATH)
    if not os.path.isdir(ACTIVE_CONFIGS_COUNTRY_PATH):
        os.mkdir(ACTIVE_CONFIGS_COUNTRY_PATH)
    if not os.path.isdir(ACTIVE_CONFIGS_RESULT_PATH):
        os.mkdir(ACTIVE_CONFIGS_RESULT_PATH)
        
    if not os.path.isdir(CHECKHOST_CONFIGS_PATH):
        os.mkdir(CHECKHOST_CONFIGS_PATH)
    if not os.path.isdir(CHECKHOST_CONFIGS_COUNTRY_PATH):
        os.mkdir(CHECKHOST_CONFIGS_COUNTRY_PATH)
    if not os.path.isdir(CHECKHOST_CONFIGS_RESULT_PATH):
        os.mkdir(CHECKHOST_CONFIGS_RESULT_PATH)
    
    if os.path.isfile(JOSN_OUTPUT_PATH):
        os.remove(JOSN_OUTPUT_PATH)
    
    if os.path.isfile(PING_TEST_PATH):
        os.chmod(PING_TEST_PATH, 0o775)
    else:
        with open(PING_TEST_PATH, "w") as f:
            f.write("test")
        os.chmod(PING_TEST_PATH, 0o775)

    # if not os.path.isdir("subs/results"):
    #     os.mkdir("subs/results")
    # if not os.path.isdir("subs/results/ping"):
    #     os.mkdir("subs/results/ping")
    # if not os.path.isdir("subs/results/speed"):
    #     os.mkdir("subs/results/speed")
    # if not os.path.isdir("subs/results/check_host"):
    #     os.mkdir("subs/results/check_host")

allowable_types = ["mixed", "base64", "clash", "hiddify", "nika", "v2ray"]

def run_command(command):
    try:
        # subprocess.run(command, text=True, shell=True)
        subprocess.call(command, shell=True)
    except TimeoutError as e:
        print(e)

def download(url: str, fname: str):
    if os.path.isfile(fname):
        os.remove(fname)
    resp = requests.get(url, stream=True)
    total = int(resp.headers.get('content-length', 0))
    # Can also replace 'file' with a io.BytesIO object
    with open(fname, 'wb') as file, tqdm(
        desc=fname,
        total=total,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)

def encode_str_to_base64(text:str):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def decode_base64_to_str(b64:str):
    return base64.b64decode(b64).decode("utf-8")

def loading_process_part(index, run, total):
	animation_frames = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]
	index_frame = index % len(animation_frames)
	process_string = "{ info }" + " loading data from result data " + animation_frames[index_frame]
	return process_string

# ---------------           Raw             ------------------
def country_flag(iso_code: str):
    emoji = {
        'AD': '🇦🇩', 'AE': '🇦🇪', 'AF': '🇦🇫', 'AG': '🇦🇬',
        'AI': '🇦🇮', 'AL': '🇦🇱', 'AM': '🇦🇲', 'AO': '🇦🇴',
        'AQ': '🇦🇶', 'AR': '🇦🇷', 'AS': '🇦🇸', 'AT': '🇦🇹',
        'AU': '🇦🇺', 'AW': '🇦🇼', 'AX': '🇦🇽', 'AZ': '🇦🇿',
        'BA': '🇧🇦', 'BB': '🇧🇧', 'BD': '🇧🇩', 'BE': '🇧🇪',
        'BF': '🇧🇫', 'BG': '🇧🇬', 'BH': '🇧🇭', 'BI': '🇧🇮',
        'BJ': '🇧🇯', 'BL': '🇧🇱', 'BM': '🇧🇲', 'BN': '🇧🇳',
        'BO': '🇧🇴', 'BQ': '🇧🇶', 'BR': '🇧🇷', 'BS': '🇧🇸',
        'BT': '🇧🇹', 'BV': '🇧🇻', 'BW': '🇧🇼', 'BY': '🇧🇾',
        'BZ': '🇧🇿', 'CA': '🇨🇦', 'CC': '🇨🇨', 'CD': '🇨🇩',
        'CF': '🇨🇫', 'CG': '🇨🇬', 'CH': '🇨🇭', 'CI': '🇨🇮',
        'CK': '🇨🇰', 'CL': '🇨🇱', 'CM': '🇨🇲', 'CN': '🇨🇳',
        'CO': '🇨🇴', 'CR': '🇨🇷', 'CU': '🇨🇺', 'CV': '🇨🇻',
        'CW': '🇨🇼', 'CX': '🇨🇽', 'CY': '🇨🇾', 'CZ': '🇨🇿',
        'DE': '🇩🇪', 'DJ': '🇩🇯', 'DK': '🇩🇰', 'DM': '🇩🇲',
        'DO': '🇩🇴', 'DZ': '🇩🇿', 'EC': '🇪🇨', 'EE': '🇪🇪',
        'EG': '🇪🇬', 'EH': '🇪🇭', 'ER': '🇪🇷', 'ES': '🇪🇸',
        'ET': '🇪🇹', 'EU': '🇪🇺', 'FI': '🇫🇮', 'FJ': '🇫🇯',
        'FK': '🇫🇰', 'FM': '🇫🇲', 'FO': '🇫🇴', 'FR': '🇫🇷',
        'GA': '🇬🇦', 'GB': '🇬🇧', 'GD': '🇬🇩', 'GE': '🇬🇪',
        'GF': '🇬🇫', 'GG': '🇬🇬', 'GH': '🇬🇭', 'GI': '🇬🇮',
        'GL': '🇬🇱', 'GM': '🇬🇲', 'GN': '🇬🇳', 'GP': '🇬🇵',
        'GQ': '🇬🇶', 'GR': '🇬🇷', 'GS': '🇬🇸', 'GT': '🇬🇹',
        'GU': '🇬🇺', 'GW': '🇬🇼', 'GY': '🇬🇾', 'HK': '🇭🇰',
        'HM': '🇭🇲', 'HN': '🇭🇳', 'HR': '🇭🇷', 'HT': '🇭🇹',
        'HU': '🇭🇺', 'ID': '🇮🇩', 'IE': '🇮🇪', 'IL': '🇮🇱',
        'IM': '🇮🇲', 'IN': '🇮🇳', 'IO': '🇮🇴', 'IQ': '🇮🇶',
        'IR': '🇮🇷', 'IS': '🇮🇸', 'IT': '🇮🇹', 'JE': '🇯🇪',
        'JM': '🇯🇲', 'JO': '🇯🇴', 'JP': '🇯🇵', 'KE': '🇰🇪',
        'KG': '🇰🇬', 'KH': '🇰🇭', 'KI': '🇰🇮', 'KM': '🇰🇲',
        'KN': '🇰🇳', 'KP': '🇰🇵', 'KR': '🇰🇷', 'KW': '🇰🇼',
        'KY': '🇰🇾', 'KZ': '🇰🇿', 'LA': '🇱🇦', 'LB': '🇱🇧',
        'LC': '🇱🇨', 'LI': '🇱🇮', 'LK': '🇱🇰', 'LR': '🇱🇷',
        'LS': '🇱🇸', 'LT': '🇱🇹', 'LU': '🇱🇺', 'LV': '🇱🇻',
        'LY': '🇱🇾', 'MA': '🇲🇦', 'MC': '🇲🇨', 'MD': '🇲🇩',
        'ME': '🇲🇪', 'MF': '🇲🇫', 'MG': '🇲🇬', 'MH': '🇲🇭',
        'MK': '🇲🇰', 'ML': '🇲🇱', 'MM': '🇲🇲', 'MN': '🇲🇳',
        'MO': '🇲🇴', 'MP': '🇲🇵', 'MQ': '🇲🇶', 'MR': '🇲🇷',
        'MS': '🇲🇸', 'MT': '🇲🇹', 'MU': '🇲🇺', 'MV': '🇲🇻',
        'MW': '🇲🇼', 'MX': '🇲🇽', 'MY': '🇲🇾', 'MZ': '🇲🇿',
        'NA': '🇳🇦', 'NC': '🇳🇨', 'NE': '🇳🇪', 'NF': '🇳🇫',
        'NG': '🇳🇬', 'NI': '🇳🇮', 'NL': '🇳🇱', 'NO': '🇳🇴',
        'NP': '🇳🇵', 'NR': '🇳🇷', 'NU': '🇳🇺', 'NZ': '🇳🇿',
        'OM': '🇴🇲', 'PA': '🇵🇦', 'PE': '🇵🇪', 'PF': '🇵🇫',
        'PG': '🇵🇬', 'PH': '🇵🇭', 'PK': '🇵🇰', 'PL': '🇵🇱',
        'PM': '🇵🇲', 'PN': '🇵🇳', 'PR': '🇵🇷', 'PS': '🇵🇸',
        'PT': '🇵🇹', 'PW': '🇵🇼', 'PY': '🇵🇾', 'QA': '🇶🇦',
        'RE': '🇷🇪', 'RO': '🇷🇴', 'RS': '🇷🇸', 'RU': '🇷🇺',
        'RW': '🇷🇼', 'SA': '🇸🇦', 'SB': '🇸🇧', 'SC': '🇸🇨',
        'SD': '🇸🇩', 'SE': '🇸🇪', 'SG': '🇸🇬', 'SH': '🇸🇭',
        'SI': '🇸🇮', 'SJ': '🇸🇯', 'SK': '🇸🇰', 'SL': '🇸🇱',
        'SM': '🇸🇲', 'SN': '🇸🇳', 'SO': '🇸🇴', 'SR': '🇸🇷',
        'SS': '🇸🇸', 'ST': '🇸🇹', 'SV': '🇸🇻', 'SX': '🇸🇽',
        'SY': '🇸🇾', 'SZ': '🇸🇿', 'TC': '🇹🇨', 'TD': '🇹🇩',
        'TF': '🇹🇫', 'TG': '🇹🇬', 'TH': '🇹🇭', 'TJ': '🇹🇯',
        'TK': '🇹🇰', 'TL': '🇹🇱', 'TM': '🇹🇲', 'TN': '🇹🇳',
        'TO': '🇹🇴', 'TR': '🇹🇷', 'TT': '🇹🇹', 'TV': '🇹🇻',
        'TW': '🇹🇼', 'TZ': '🇹🇿', 'UA': '🇺🇦', 'UG': '🇺🇬',
        'UM': '🇺🇲', 'US': '🇺🇸', 'UY': '🇺🇾', 'UZ': '🇺🇿',
        'VA': '🇻🇦', 'VC': '🇻🇨', 'VE': '🇻🇪', 'VG': '🇻🇬',
        'VI': '🇻🇮', 'VN': '🇻🇳', 'VU': '🇻🇺', 'WF': '🇼🇫',
        'WS': '🇼🇸', 'XK': '🇽🇰', 'YE': '🇾🇪', 'YT': '🇾🇹',
        'ZA': '🇿🇦', 'ZM': '🇿🇲', 'ZW': '🇿🇼',
        'RELAY': '🏁',
        'NOWHERE': '🇦🇶',
    }
    
    if iso_code in emoji.keys():
        return emoji[iso_code]
    else:
        return emoji['NOWHERE']

async def rename_configs_online(new_configs):
    confs_len = len(new_configs)
    renamed_config = []
    chunk_size = confs_len
    counter = 0
    while len(new_configs) > 0:
        tasks = []
        renaming_configs = []
        print(f"renaming configs : {counter}/{confs_len}", end="\r")
        counter += chunk_size
        for i in range(chunk_size):
            if len(new_configs) == 0:
                break
            conf = new_configs.pop(0).strip()
            if conf.startswith("ss://"):
                try:
                    ip = conf.split("@")[1].split("#")[0].split(":")[0]
                    port = conf.split("@")[1].split("#")[0].split(":")[1]
                    renaming_configs.append(conf)
                    tasks.append(find_ip_location_online(ip, port, conf))
                except:
                    print(conf)
        if len(tasks) > 0:
            check_result = await asyncio.gather(*tasks)
            for _conf in check_result:
                renamed_config.append(_conf)
    print(f"renaming configs : {confs_len}/{confs_len}")
    return renamed_config

async def find_ip_location_online(ip, port, conf, timeout = 2):
    def ip_location():
        try:
            if not ip.replace(".", "").isdigit():
                try:
                    ip = socket.gethostbyname(ip)
                except:
                    pass
            res = requests.get(f"https://api.iplocation.net/?ip={ip}", timeout = timeout)
            data = json.loads(res.text)
            _locc = data["country_code2"]
            name = f"{_locc} - {ip}:{port}"
            return conf.split("#")[0] + f"#{name}"
        except:
            return False
    return await asyncio.to_thread(ip_location)

def raname_configs(new_configs, check_city = True, force_online = False):
    
    def find_country_from_geopip(ip):
        try:
            data = country_reader.country(ip)
            return data.country.iso_code, data.country.name
        except:
            return "NOWHERE"

    def find_city_and_country_from_geopip(ip):
        try:
            data = city_reader.city(ip)
            return data.country.iso_code, data.country.name, data.city.name
        except:
            return "NOWHERE"

    if force_online:
        return asyncio.run(rename_configs_online(new_configs))
    else:
        if os.path.isfile(GEOLITE_CITY_PATH) and check_city:
            city_reader = geoip2.database.Reader(GEOLITE_CITY_PATH)
            is_city_availabe = True
        else:
            if os.path.isfile(GEOLITE_COUNTRY_PATH):
                country_reader = geoip2.database.Reader(GEOLITE_COUNTRY_PATH)
                is_city_availabe = False
            else:
                return asyncio.run(rename_configs_online(new_configs))
    
    renamed_configs = []
    errored_config = []
    for conf in new_configs:
        try:
            ip = conf.split("@")[1].split("#")[0].split(":")[0]
            if ip == "127.0.0.1":
                continue
            if not ip.replace(".", "").isdigit():
                try:
                    ip = socket.gethostbyname(ip)
                except:
                    pass
            port = conf.split("@")[1].split("#")[0].split(":")[1]
            if is_city_availabe:
                iso_code, country, city = find_city_and_country_from_geopip(ip)
                try:
                    flg = country_flag(iso_code)
                    name = f"{flg} {iso_code} {city}"
                except:
                    name = f"{iso_code} {city}"
            else:
                iso_code, country = find_country_from_geopip(ip)
                try:
                    flg = country_flag(iso_code)
                    name = f"{flg} {iso_code}"
                except:
                    name = f"{iso_code}"
            renamed_configs.append(f"{conf.split('#')[0]}#{name}")
        except:
            errored_config.append(conf)
            # print(f"error in rename offlien: {conf}")
    return renamed_configs

def merge_two_list(l1, l2):
    l3 = []
    ips_ports = []
    for item in l1:
        if item.strip():
            item = item.replace("/?POST%20", "").strip()
            ip_port = item.split("@")[1].split("#")[0]
            if not ip_port in ips_ports and ip_port.split(":")[0] != "127.0.0.1":
                ips_ports.append(ip_port)
                l3.append(item.strip())

        
    for item in l2:
        if item.strip():
            item = item.replace("/?POST%20", "").strip()
            ip_port = item.split("@")[1].split("#")[0]
            if not ip_port in ips_ports and ip_port.split(":")[0] != "127.0.0.1":
                ips_ports.append(ip_port)
                l3.append(item.strip())
    return list(set(l3))

def convert_to_mixed(text, typ):
    confs = []
    _confs = []
    if typ == "mixed":
        _confs = text.splitlines()
    elif typ == "base64":
        _confs = base64.b64decode(text).decode("utf-8").splitlines()
    elif typ == "json":
        js = json.loads(text)
        for item in js:
            b = encode_str_to_base64(f'{item.get("method")}:{item.get("password")}')
            # b = base64.b64encode(f'{item.get("method")}:{item.get("password")}'.encode('utf-8')).decode('utf-8')
            _confs.append(f'ss://{b}@{item.get("server")}:{item.get("server_port")}#SS')

    for item in _confs:
        # try:
            item = item.strip().replace("`", "").replace("/?POST%20", "")
            if not item.startswith("ss://"):
                continue
            if item.startswith("ss://ey"):
                continue
            if "security=" in item:
                continue
            
            if "#" not in item:
                item += "#SS"
            if len(item.split("#")) == 2:
                _body_b64 = item.replace("ss://", "").split("#")[0]
                if "@" not in _body_b64:
                    _body_str = decode_base64_to_str(_body_b64)
                    if "@" in _body_str:
                        _method_pass = encode_str_to_base64(_body_str.split("@")[0])
                        ip_port = _body_str.split("@")[1]
                        if ip_port.split(":")[0] == "127.0.0.1":
                            continue
                        item = f'ss://{_method_pass}@{ip_port}#SS'
                    else:
                        continue
            else:
                continue
            if item:
                confs.append(unquote(item))
        # except Exception as e:
        #     print(item)
        #     print(e)
            
    return confs

def check_config_duplicate(configs, old_configs):
    def find_ip_port(conf):
        conf = conf.strip()
        if conf.startswith("ss://"):
            try:
                return conf.split("@")[1].split("#")[0]
            except:
                return False
    
    if len(old_configs) == 0:
        return configs
    old_configs = list(set(old_configs))
    old_ip_ports = []
    unique_configs = []
    new_configs = []
    for _c in old_configs:
        old_ip_ports.append(find_ip_port(_c))
    for _c_ in configs:
        if find_ip_port(_c_) not in old_ip_ports:
            new_configs.append(_c_)
    return new_configs
        
def save_all_configs():
    with open("utils/urls.json") as f:
        alldata  = json.load(f)
    for sub in alldata["subs"]:
        try:
            new_configs = []
            urls = []
            name = sub.get("name")
            print(f"\nprocess subs: {name}")
            if isinstance(sub["url"], str):
                urls.append(sub["url"])
            if isinstance(sub["url"], list):
                for u in sub["url"]:
                    urls.append(u)
            print(f"found {len(urls)} url")
            for url in urls:
                if not url.startswith("https"):
                    url = "https://" + url
                try:
                    res = requests.get(url, timeout = 5)
                except:
                    print(f"trouble to reaching: {url}")
                    continue
                text = res.text
                _new_config = convert_to_mixed(text, sub["type"])
                for item in _new_config:
                    new_configs.append(item)
            if len(new_configs) == 0:
                print(f"we don't found any config in {name}")
                continue
            
            old_configs = []
            if os.path.isfile(f"{RAW_CONFIGS_PROVIDER_PATH}/{name}.txt"):
                with open(f"{RAW_CONFIGS_PROVIDER_PATH}/{name}.txt", encoding="utf-8-sig") as f:
                    old_configs = f.readlines()
                    old_configs = [item.strip() for item in old_configs]
            new_configs = check_config_duplicate(new_configs, old_configs)
            print(f"found {len(new_configs)} new configs")
            if len(new_configs) > 0:
                renamed_configs = raname_configs(new_configs)
                # renamed_configs = asyncio.run(rename_configs_online(new_configs))
                # print(renamed_configs)
                merge_configs = merge_two_list(renamed_configs, old_configs)
                with open(f"{RAW_CONFIGS_PROVIDER_PATH}/{name}.txt", "w", encoding="utf-8-sig") as f:
                    for i, item in enumerate(merge_configs):
                        if i + 1 == len(merge_configs):
                            f.write(f"{item}")
                        else:
                            f.write(f"{item}\n")
        except Exception as e:
            print(f"error in sub: {sub.get('name')}")
            print(e)

def merge_all_configs():
    with open("utils/urls.json") as f:
        alldata  = json.load(f)
    _all_configs = []
    for sub in alldata["subs"]:
        name = sub.get("name")
        if os.path.isfile(f"{RAW_CONFIGS_PROVIDER_PATH}/{name}.txt"):
            with open(f"{RAW_CONFIGS_PROVIDER_PATH}/{name}.txt", encoding="utf-8-sig") as f:
                sub_configs = f.readlines()
        for item in sub_configs:
            _all_configs.append(unquote(item).strip())
    unique_configs = list(set(_all_configs))
    
    print(f"All Configs = {len(_all_configs)}\tUnique Configs = {len(unique_configs)}")
    
    with open(f"{RAW_CONFIGS_PATH}/all.txt","w", encoding="utf-8-sig") as f:
        for i, item in enumerate(unique_configs):
            if i + 1 == len(unique_configs):
                f.write(f"{item}")
            else:
                f.write(f"{item}\n")

def split_raw_by_country():
    print("Split 'Raw' configs based on Country ....")
    with open(f"{RAW_CONFIGS_PATH}/all.txt", encoding="utf-8-sig") as f:
        data = f.readlines()
    splited_country = {}
    for item in data:
        conf = unquote(item).strip()
        if len(conf.split("#")) == 2:
            full_name = conf.split("#")[1]
            if len(full_name.split(" ")) == 3:
                country = full_name.split(" ")[1]
                if splited_country.get(country):
                    splited_country[country].append(conf)
                else:
                    splited_country[country] = [conf]
                    
    for _c, confs in splited_country.items():
        with open(f"{RAW_CONFIGS_COUNTRY_PATH}/{_c}.txt", "w", encoding="utf-8-sig") as f:
            for item in confs:
                f.write(item)
                f.write("\n")

# ---------------           Active          ------------------
def kill_pid(pid):        
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def is_speedtest_ended(log_path):
    if os.path.isfile(log_path):
        with open(log_path, "r") as f:
            data = f.readlines()
        try:
            if json.loads(data[-1].split()[-1]).get("id") == -1:
                return True
        except:
            pass
    return False
        
def ping_all_configs():
    is_windows = True if os.sys.platform.lower()=='win32' else False
    if is_windows:
        zip_file = f".\\{TEMP_PATH}\\lite-windows-amd64-v0.15.0.zip"
        exe_file = "lite-windows-amd64.exe"
        config_temp_path = f".\\{TEMP_PATH}\\temp.txt"
        temp_result_path = f".\\{TEMP_PATH}\\results\\"
        result_path = ACTIVE_CONFIGS_RESULT_PATH
        url = "https://github.com/xxf098/LiteSpeedTest/releases/download/v0.15.0/lite-windows-amd64-v0.15.0.zip"
        if not os.path.isfile(exe_file):
            if os.path.isfile(zip_file):
                os.remove(zip_file)
            download(url, zip_file)
            with ZipFile(zip_file, 'r') as z:
                z.extractall()
            if not os.path.isfile(exe_file):
                return
    else:
        gz_file = "lite-linux-amd64.gz"
        exec_file = "lite-linux-amd64"
        config_temp_path = f"{TEMP_PATH}/temp.txt"
        temp_result_path = f"{TEMP_PATH}/results/"
        result_path = ACTIVE_CONFIGS_RESULT_PATH
        url = "https://github.com/xxf098/LiteSpeedTest/releases/download/v0.15.0/lite-linux-amd64-v0.15.0.gz"
        if not os.path.isfile(exec_file):
            if os.path.isfile(gz_file):
                os.remove(gz_file)
            run_command(f"wget -O {gz_file} {url}")
            time.sleep
            run_command(f"gzip -d {gz_file}")
            time.sleep(2)
            run_command(f"chmod +x ./{exec_file}")
            if not os.path.isfile(exec_file):
                return

    if not os.path.isdir(temp_result_path):
        os.mkdir(temp_result_path)
    else:
        _files = os.listdir(temp_result_path)
        for _file in _files:
            _file_path = os.path.join(temp_result_path, _file)
            os.remove(_file_path)

    with open(f"{RAW_CONFIGS_PATH}/all.txt", encoding="utf-8-sig") as f:
    # with open(f"{RAW_CONFIGS_PROVIDER_PATH}/ainita.txt", encoding="utf-8-sig") as f:
        all_configs = f.readlines()
        all_configs = [item.strip() for item in all_configs]    

    CHUNK_SIZE = 100
    CHUNK_TIMEOUT = 150     # sec
    counter = 1
    start_total = time.time()
    batch_run = 0
    print(f"Start Testing {len(all_configs)} configs")
    while len(all_configs) > 0:
        print(f"all configs = {len(all_configs)}")
        if os.path.isfile(JOSN_OUTPUT_PATH):
            os.remove(JOSN_OUTPUT_PATH)
        if os.path.isfile(SPEEDTEST_LOG_PATH):
            os.remove(SPEEDTEST_LOG_PATH)
        start_chuck_time = time.time()
        temp_configs = []
        if len(all_configs) > CHUNK_SIZE:
            for i in range(CHUNK_SIZE):
                temp_configs.append(all_configs.pop(random.randint(0, len(all_configs) - 1)))
            # temp_configs = all_configs[0:CHUNK_SIZE].copy()
        else:
            temp_configs = all_configs.copy()
            all_configs = []
            

        with open(config_temp_path, "w", encoding="utf-8-sig") as f:
            for item in temp_configs:
                f.write(item)
                f.write("\n")
        
        # run_command
        if is_windows:
            cmd = f'.\\\\{exe_file} --config utils/ping_config.json --test {TEMP_PATH}/temp.txt > {SPEEDTEST_LOG_PATH} 2>&1 &'
        else:
            cmd = f"./{exec_file} --config utils/ping_config.json --test {config_temp_path} > {SPEEDTEST_LOG_PATH} 2>&1 &"
        
        with open(PING_TEST_PATH, "w") as f:
            f.write(cmd)
        
        process = subprocess.Popen(["sh", PING_TEST_PATH], stdout=subprocess.PIPE)
        process.wait()
        pid = process.pid
        
        if batch_run == 0:
            if CHUNK_SIZE < len(all_configs):
                batch_run = ceil(len(all_configs)/CHUNK_SIZE)
                max_run = batch_run * 2
            else:
                batch_run = 1
                max_run = 2
        
        # wait for output.json file exists and process ends
        while not os.path.isfile(JOSN_OUTPUT_PATH):
            print(f'waiting for ping test to comaplete, run: {counter} of {batch_run}\telapsed_time: {int((time.time() - start_total)/60)} min')
            time.sleep(10)
            if time.time() - start_chuck_time > CHUNK_TIMEOUT:
                break
            if is_speedtest_ended(SPEEDTEST_LOG_PATH):
                break
            # if process.poll() is not None:
            #     break
            
        # terminate process after completion
        if is_windows:
            # subprocess.call(f"taskkill -f -im lite-windows-amd64*", shell=True)
            kill_pid(pid)
        else:
            subprocess.call(f"sudo pkill -f {exec_file}", shell=True)
                
        # extract ping nun zero
        if os.path.isfile(JOSN_OUTPUT_PATH):
            counter += 1
            with open(JOSN_OUTPUT_PATH, encoding="utf-8") as f:
                js = json.load(f)
            output_servers = []
            for item in js["nodes"]:
                out = f"{unquote(item['link']).strip()},{int(item['ping'])}"
                output_servers.append(out)
                # if item["ping"] != "0":
                #     out = {"Config": unquote(item["link"]).strip(), "Ping": int(item["ping"])}
                #     output_servers.append(out)
            if len(output_servers) > 0:
                name = f"{temp_result_path}{counter}.txt"
                with open(name, "w", encoding="utf-8-sig") as f:
                    for s in output_servers:
                        f.write(f"{s}")
                        # f.write(s)
                        f.write("\n")
        else:
            for item in temp_configs:
                all_configs.append(item)
                    
        if counter > max_run:
            break
        
        time.sleep(2)
    
    # merge all results
    results_jsonl = []
    _files = os.listdir(temp_result_path)
    for _file in _files:
        _file_path = os.path.join(temp_result_path, _file)
        with open(_file_path, encoding="utf-8-sig") as f:
            _data = f.readlines()
        for _c in _data:
            results_jsonl.append(_c.strip())
    if len(all_configs) > 0:
        for item in all_configs:
            out = f"{unquote(item).strip()},0"
            results_jsonl.append(out)
    raw_cofigs = []
    if len(results_jsonl) > 0:
        with open(f"{result_path}/{NOW}.txt", "w", encoding="utf-8-sig") as f:
            f.write("Config,Ping")
            f.write("\n")
            for item in results_jsonl:
                f.write(f"{item}")
                f.write("\n")
                if item.split(",")[1] != "0":
                    raw_cofigs.append(item.split(",")[0].strip())
        with open(f"{ACTIVE_CONFIGS_PATH}/all.txt", "w", encoding="utf-8-sig") as f:
            for item in raw_cofigs:
                f.write(f"{item}")
                f.write("\n")

def split_active_by_country():
    print("Split 'Active' configs based on Country ....")
    with open(f"{ACTIVE_CONFIGS_PATH}/all.txt", encoding="utf-8-sig") as f:
        data = f.readlines()
    if data[0].strip().split(",")[0] == "Config":
        data.pop(0)
    splited_country = {}
    for item in data:
        conf = unquote(item.split(",")[0]).strip()
        if len(conf.split("#")) == 2:
            full_name = conf.split("#")[1]
            if len(full_name.split(" ")) == 3:
                country = full_name.split(" ")[1]
                if splited_country.get(country):
                    splited_country[country].append(conf)
                else:
                    splited_country[country] = [conf]
                    
    for _c, confs in splited_country.items():
        with open(f"{ACTIVE_CONFIGS_COUNTRY_PATH}/{_c}.txt", "w", encoding="utf-8-sig") as f:
            for item in confs:
                f.write(item)
                f.write("\n")

# ---------------           Check-host      ------------------
def check_host_configs(confs):
    error = 0
    all_data = []
    while len(confs) > 0:
        conf = confs.pop(0)
        # print(conf)
        try:
            ip = conf.split("@")[1].split("#")[0].split(":")[0]
            # print("\n")
            # print(ip)
            data = ping_part(ip)
            if data:
                time.sleep(random.randint(100, 1000) / 1000)
                data = conf.strip() + "," + data
                all_data.append(data)
            else:
                time.sleep(random.randint(2000, 5000) / 1000)
                print("reached API limit, wait a sec.")
                confs.append(ip)
                error += 1
            if error > 10:
                break    
        except Exception as e:
            time.sleep(random.randint(2000, 5000) / 1000)
            print(f"Error in conf: {conf}")
            print(e)
    return all_data

def process_check_host_results(confs):
    check_host_results = check_host_configs(confs)
    new_configs = []
    if len(check_host_results) > 0:
        for item in check_host_results:
            new_configs.append(item)
    if len(new_configs) > 0:
        name = f"{CHECKHOST_CONFIGS_RESULT_PATH}/all.txt"
        old_configs = []
        if os.path.isfile(name):
            with open(name, encoding="utf-8-sig") as f:
                old_configs = f.readlines()
        with open(name, "w", encoding="utf-8-sig") as f:
            for _c in old_configs:
                if _c.strip():
                    f.write(f"{_c.strip()}")
            for _c in new_configs:
                f.write(f"{_c}")
                f.write("\n")
    
def check_host():
    with open(f"{ACTIVE_CONFIGS_PATH}/all.txt", encoding="utf-8-sig") as f:
        configs = f.readlines()
    batch_size = 100
    if len(configs) > batch_size:
        batch_configs = []
        while len(batch_configs) < batch_size and len(configs) > 0:
            conf = configs.pop(0).strip()
            if conf:
                batch_configs.append(conf)
        process_check_host_results(batch_configs)
    else:
        process_check_host_results(configs)


if __name__ == "__main__":
    setup_env()
    save_all_configs()
    merge_all_configs()
    split_raw_by_country()
    ping_all_configs()
    split_active_by_country()
    # check_host_country("AM")
