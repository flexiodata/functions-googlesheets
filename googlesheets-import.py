
# ---
# name: googlesheets-import
# deployed: true
# title: Google Sheets Import
# description: Creates functions to access sheets from Google Sheets
# ---

import base64
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
        flex.index.create(function_info['name'], file_id)

def to_date(value):
    return value

def to_string(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (Decimal)):
        return str(value)
    return value

def get_function_info(connection_info, table):

    table = f.get('name')

    # return the function info
    info = {}
    info['name'] = 'googlesheets-' + table.lower() # TODO: make clean name
    info['title'] = ''
    info['description'] = ''
    info['task'] = {
        'op': 'sequence',
        'items': [{
            'op': 'execute',
            'lang': 'python',
            'code': get_function_extract_task(table)
        }]
    }
    info['returns'] = column_info
    info['run_mode'] = 'P'
    info['deploy_mode'] = 'R'
    info['deploy_api'] = 'A'

    return info

def get_function_extract_task(table):
    code = """

import json
import urllib
import itertools
from datetime import *
from decimal import *
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

    # TODO: get table data from API

def to_string(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (Decimal)):
        return str(value)
    return value

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

