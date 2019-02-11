import os
import subprocess
import uuid
from copy import deepcopy
from typing import Dict

import boto3
from botocore.client import Config as BotoCoreClientConfig
from botocore.handlers import set_list_objects_encoding_type_url
from celery import Celery

app = Celery('chowder')
app.config_from_object('chowder.celeryconfig')


def _create_s3_resource(resource_config: Dict, disable_encoding_type: bool):
    my_resource_config = deepcopy(resource_config)
    my_resource_config['config'] = BotoCoreClientConfig(**my_resource_config['config'])

    session = boto3.session.Session()
    if disable_encoding_type:
        session.events.unregister('before-parameter-build.s3.ListObjects', set_list_objects_encoding_type_url)

    return session.resource('s3', **my_resource_config)


@app.task(bind=True)
def scan_s3_object(self,
                   resource_config: Dict,
                   bucket: str,
                   key: str,
                   disable_encoding_type: bool = False,
                   timeout: int = 3600,
                   clamscan_options: Dict[str, str] = None):
    if clamscan_options is None:
        clamscan_options = {}
    if 'max-filesize' not in clamscan_options:
        clamscan_options['max-filesize'] = 0
    if 'max-scansize' not in clamscan_options:
        clamscan_options['max-scansize'] = 0

    temp_dir = clamscan_options['tempdir'] if 'tempdir' in clamscan_options else '/tmp'
    temp_file = '{}/{}'.format(temp_dir, uuid.uuid4().hex)
    try:
        s3_resource = _create_s3_resource(resource_config, disable_encoding_type)
        s3_resource.Object(bucket, key).download_file(temp_file)
    except Exception as exception:
        try:
            os.unlink(temp_file)
        except FileNotFoundError:
            pass
        # Make sure to translate exception into a universally known one
        raise RuntimeError(f'S3 GET operation failed: {str(exception)}')

    clamscan_invocation = ['clamscan']
    clamscan_invocation.extend(
        [('--' if len(option_name) > 1 else '-') + option_name + ('=' if option_value is not None else '') +
         (str(option_value) if option_value is not None else '')
         for option_name, option_value in clamscan_options.items()])
    clamscan_invocation.append(temp_file)

    print(clamscan_invocation)

    try:
        result = subprocess.run(
            clamscan_invocation,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout)
    except Exception as exception:
        raise RuntimeError(f'clamscan subprocess failed: {str(exception)}')
    finally:
        os.unlink(temp_file)

    # Remove temporary filename from output
    result_output = result.stdout.replace(temp_file + ': ', '')

    if result.returncode == 0:
        # No virus found
        return False, result_output
    elif result.returncode == 1:
        # Virus found
        return True, result_output
    else:
        raise RuntimeError(f'clamscan invocation failed with return code {result.returncode} and output: ' +
                           result_output.replace('\n', ', '))
