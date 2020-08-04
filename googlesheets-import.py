
# ---
# name: googlesheets-import
# deployed: true
# title: Google Sheets Import
# description: Creates functions to access sheets from Google Sheets
# ---

import base64
import re
from datetime import *
from decimal import *

# main function entry point
def flex_handler(flex):
    create_functions(flex)

def create_functions(flex):

    # get the parameters
    params = dict(flex.vars)
    files = params['files']
    connection_info = params['googlesheets-connection']

    # create functions for each of the selected sheets
    for f in files:

        function_info = get_function_info(connection_info, f)
        flex.index.remove(function_info['name'])
        flex.index.create(function_info['name'], function_info)

def to_date(value):
    return value

def to_string(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (Decimal)):
        return str(value)
    return value

def get_function_info(connection_info, sheet):

    sheet_id = sheet.get('id')
    sheet_name = sheet.get('name').lower()
    clean_name = 'googlesheets-' + re.sub('[^0-9a-zA-Z]+', '-', sheet_name)
    column_info = []

    # return the function info
    info = {}
    info['name'] = clean_name
    info['title'] = ''
    info['description'] = ''
    info['task'] = {
        'op': 'sequence',
        'items': [{
            'op': 'execute',
            'lang': 'python',
            'code': get_function_extract_task(sheet)
        }]
    }
    info['returns'] = column_info
    info['run_mode'] = 'P'
    info['deploy_mode'] = 'R'
    info['deploy_api'] = 'A'

    return info

def get_function_extract_task(sheet):
    code = """

import json
import urllib
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import itertools
from cerberus import Validator
from collections import OrderedDict

# main function entry point
def flex_handler(flex):

    # get the input
    input = flex.input.read()
    input = json.loads(input)
    if not isinstance(input, list):
        input = []

    # define the expected parameters and map the values to the parameter names
    # based on the positions of the keys/values
    params = OrderedDict()
    params['properties'] = {'required': False, 'validator': validator_list, 'coerce': to_list, 'default': '*'}
    params['filter'] = {'required': False, 'type': 'string', 'default': ''}
    params['config'] = {'required': False, 'type': 'string', 'default': ''} # index-styled config string
    input = dict(zip(params.keys(), input))

    # validate the mapped input against the validator
    v = Validator(params, allow_unknown = True)
    input = v.validated(input)
    if input is None:
        raise ValueError

    # get the properties to return and the property map;
    # if we have a wildcard, get all the properties
    properties = [p.strip() for p in input['properties']]
    if len(properties) == 1 and (properties[0] == '' or properties[0] == '*'):
        properties = ['*']

    # get the filter
    filter = input['filter']
    if len(filter) == 0:
        filter = 'True'

    # get any configuration settings
    config = urllib.parse.parse_qs(input['config'])
    config = {k: v[0] for k, v in config.items()}
    limit = int(config.get('limit', 100))
    headers = config.get('headers', 'true').lower()
    if headers == 'true':
        headers = True
    else:
        headers = False

    # get the connection info
    params = dict(flex.vars)
    files = params['files']
    connection_info = params['googlesheets-connection']

    # query the sheet
    auth_token = connection_info.get('access_token')
    headers = {
        'Authorization': 'Bearer ' + auth_token,
    }

    spreadsheet_id = '""" + sheet.get('id','') + """'
    worksheet_title = '""" + sheet.get('name','') + """'
    url = 'https://sheets.googleapis.com/v4/spreadsheets/' + spreadsheet_id + '/values/' + worksheet_title

    response = requests_retry_session().get(url, headers=headers)
    response.raise_for_status()
    content = response.json()
    values = content.get('values',[['']])

    max_row_length = 0
    for row in values:
        current_row_length = len(row)
        if current_row_length > max_row_length:
            max_row_length = current_row_length

    result = []
    for row in values:
        padded_row = row + ['']*(max_row_length-len(row))
        result.append(padded_row)

    flex.output.content_type = 'application/json'
    flex.output.write(result)

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(429, 500, 502, 503, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def validator_list(field, value, error):
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, str):
                error(field, 'Must be a list with only string values')
        return
    error(field, 'Must be a string or a list of strings')

def to_list(value):
    # if we have a list of strings, create a list from them; if we have
    # a list of lists, flatten it into a single list of strings
    if isinstance(value, str):
        return value.split(",")
    if isinstance(value, list):
        return list(itertools.chain.from_iterable(value))
    return None

"""
    code = code.encode('utf-8')
    return base64.b64encode(code).decode('utf-8')

