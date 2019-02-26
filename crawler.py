import http.client
import requests
import json
from pprint import pprint
import re

BASE_URL = 'https://s3-ap-southeast-2.amazonaws.com/origin-neighbourhoods-similar-suburbs/mosaic/similar-suburbs-for-neighbourhoods/vic/'
SUBURB_DATA_FILENAME = "suburbs.json"
MERGED_DATA_FILENAME = "merged.json"
primary_map = {}
secondary_map = {}

DISTANCE_FIRST_SPLIT = re.compile("<div class=\"div_scroll_wide\">\r\n")
DISTANCE_ITEMS_SPLIT = re.compile("<br />")
DISTANCE_POSTCODE_DIST_SPLIT = re.compile("[a-zA-Z\(\) /><]+")

MEDIAN_PRICE_KEY = "median_sold_price"
DISTANCE_FROM_CENTER_KEY = "distance"


def start():
    secondary_map = prepare_distance_mapping()
    primary_map = prepare_suburb_map()
    primary_map = merge_maps(primary_map, secondary_map)

    with open(MERGED_DATA_FILENAME, 'w') as file:
            file.write(json.dumps(primary_map, indent=4))


def extract_suburbs(response_object, suburb_map, state='VIC'):
    list_of_suburbs = response_object.get(state)
    for s in list_of_suburbs:
        s.pop('photo')
        suburb_key = s.get('suburb')
        if suburb_key not in suburb_map:
            suburb_map[suburb_key] = s


def iterate(primary_suburb_map, secondary_suburb_map):
    for key in primary_suburb_map:
        s = primary_suburb_map[key]
        process_suburb(s, secondary_suburb_map)
        s['done'] = True


def process_suburb(s, suburb_map):
    # make api call and extract suburbs and mark it done
    if not s.get('done'):
        rel_path = s.get('suburb').lower() + '-' + s.get('postcode') + '.json'
        r = requests.get(BASE_URL+rel_path)
        print(' Executing : {}', s)
        if r.status_code > 199 and r.status_code < 300:
            response_object = r.json()
            extract_suburbs(response_object, suburb_map)


def prepare_distance_mapping(radius='25'):
    distance_map = dict()
    r = requests.get('http://www.australiapostcodes.com/ajax_results_radius?c=au&z=3000&r=' + radius)
    if r.status_code > 199 and r.status_code < 300:
        items = DISTANCE_FIRST_SPLIT.split(r.text)
        items = DISTANCE_ITEMS_SPLIT.split(items[1])
        for item in items:
            data = DISTANCE_POSTCODE_DIST_SPLIT.split(item)
            if len(data) > 2:
                postcode = data[0]
                distance = data[1]
                distance_map[postcode] = distance
    return distance_map


def prepare_suburb_map():
    main_map = {}
    backup_map = {}

    with open(SUBURB_DATA_FILENAME) as file:
        main_map = json.load(file)

    if len(main_map) == 0:
        main_map['OAKLEIGH'] = {'postcode': '3166', 'state': 'VIC',
                                'suburb': 'oakleigh'}
        progress = True

        while progress:
            iterate(main_map, backup_map)
            prev_len = len(main_map)
            main_map = dict(backup_map, **main_map)
            backup_map = dict()
            progress = len(main_map) != prev_len

        with open(SUBURB_DATA_FILENAME, 'w') as file:
            file.write(json.dumps(main_map))

    return main_map


def merge_maps(primary_map, secondary_map):
    for s in primary_map:
        postcode = primary_map[s].get('postcode')
        if 'photo' in primary_map[s]:
            primary_map[s].pop('photo')
        if postcode in secondary_map:
            primary_map[s]['distance'] = secondary_map[postcode]

    return primary_map

start()