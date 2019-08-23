#!/usr/bin/env python3
"""
Script to generate application dependency stack analysis report
"""

__author__ = "Samuzzal Choudhury"
__version__ = "0.0.1"

import requests
import glob
import os, time, json, sys
import subprocess as sp
from logzero import logger
import pkg_resources as pr


REPO_LOCATION = os.getenv('REPO_LOCATION', '/coreapi/repo')

def get_repo_ecosystem():
    ecosystem = None
    if len(glob.glob(f'{REPO_LOCATION}/package.json')) > 0:
        ecosystem = 'npm'
    elif len(glob.glob(f'{REPO_LOCATION}/requirements.txt')) > 0:
        ecosystem = 'pypi'

    logger.info('Identified ecosystem is %s' % ecosystem)
    return ecosystem


def generate_deps_file(ecosystem, manifest):
    out = None
    if ecosystem == 'npm':
        command = f'cd {REPO_LOCATION}; npm install; npm list --prod --json > {manifest}'
        logger.info(f'Generating {manifest} ...')
        out = sp.check_output(command, shell=True)
    elif ecosystem == 'pypi':
        command = f'pip3 install -r {REPO_LOCATION}/requirements.txt'
        logger.info(f'Running: {command}')
        sp.check_output(command, shell=True)
        gd = pr.get_distribution
        out = list()
        for i in open(f'{REPO_LOCATION}/requirements.txt'):
            try:
                rs = {}
                I = gd(i)
                logger.info(f'Identified {I}')
                rs["package"] = I.key
                rs["version"] = I.version
                rs["deps"] = set()
                for j in pr.require(i):
                    for k in j.requires():
                        K = gd(k)
                        rs["deps"].add((K.key, K.version))
                rs["deps"] = [{"package": p, "version": v} for p, v in rs["deps"]]
                out.append(rs)
            except:
                pass
        logger.info('Result: %r' % out)
        logger.info(f'Writing {manifest}')
        try:
            with open(f'{REPO_LOCATION}/{manifest}', "w+") as op:
                op.write(json.dumps(out, indent=4))
        except Exception as e:
            logger.error('%r' % e)
    return out

def run_sa_post(gateway_url, gateway_user_key, source='vscode'):
    """Initiate a stack-analyses call."""

    ecosystem = get_repo_ecosystem()
    if ecosystem == 'npm':
        manifest = 'npmlist.json'
    elif ecosystem == 'pypi':
        manifest = 'pylist.json'
    else:
        logger.error('Unsupported development ecosystem. Cannot initiate a stack analysis')
        return None

    if generate_deps_file(ecosystem, manifest) is None:
        logger.error('The dependencies file could not be generated. Stack analysis cannot be run.')
        return None

    logger.info(f'Initiating stack analyses')
    stack_analyses_post_ep = f"https://{gateway_url}/api/v1/stack-analyses/"
    params = (
        ('user_key', gateway_user_key),
    )
    data = {
        'manifest[]': (f'{manifest}', open(f'{REPO_LOCATION}/{manifest}', 'rb')),
        'filePath[]': (None, '{REPO_LOCATION}')
    }
    headers = {
        'ecosystem': ecosystem,
        'source': source
    }
    try:
        resp = requests.post(stack_analyses_post_ep, headers=headers, files=data, params=params)
        if resp.status_code == 200:
            logger.info('Response Json:\n%r' % resp.json())
            return resp.json().get('id')
        else:
            logger.error('The stack analyses POST request resulted in a failure. Status Code: %s, '
                         'Reason: %s, '
                         'Response: %r'
                         % (resp.status_code, resp.reason, resp.json()))
            return None
    except Exception as e:
        logger.error('Failed initiating stack analysis request. Reason: %r' % e)


def run_sa_get(gateway_url, gateway_user_key, request_id=None):
    """Retrieve the result of the stack analysis run."""

    if request_id is None:
        logger.error(f'Invalid request id {request_id}')
        return {}

    stack_analyses_get_ep = f"https://{gateway_url}/api/v1/stack-analyses"
    params = (
        ('user_key', gateway_user_key),
    )
    try:
        resp = requests.get(f'{stack_analyses_get_ep}/{request_id}', params=params)
        if resp.status_code == 200:
            logger.info('Generated response here:')
            return resp.json()
        else:
            logger.info('Could not retrieve the stack analysis response. Status code: '
                        '{resp.status_code}')
            return {}
    except Exception as e:
        logger.error('Failed retrieving stack analysis response. Reason: %r' % e)


def main():
    """ Main entry point of the app """
    logger.info("Executing main function")

    gateway_url = os.getenv('API_GATEWAY_URL')
    if not gateway_url:
        logger.error("The API management gateway URL is missing. "
                     "Set the environment variable 'API_GATEWAY_URL'")
        return

    gateway_user_key = os.getenv('API_GATEWAY_USER_KEY')
    if not gateway_user_key:
        logger.error("The API management gateway user key is missing. "
                     "Set the environment variable 'API_GATEWAY_USER_KEY'")
        return

    # Initiate stack analyses
    request_id = run_sa_post(gateway_url, gateway_user_key)

    if request_id is not None:
        logger.info('Waiting for the stack analysis response...')
        time.sleep(20)

        resp_json = run_sa_get(gateway_url, gateway_user_key, request_id)
        # logger.info(resp_json)
        with open('/coreapi/repo/response.json', 'w') as f:
            f.write(json.dumps(resp_json, indent=4))
        logger.info('Written the stack analysis response to response.json in the '
                    'repo directory')


if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()
