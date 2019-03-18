import subprocess
import uuid

from fs import open_fs
from celery import Celery
from fs.copy import copy_file
from fs.errors import ResourceNotFound

from typing import Dict, Tuple, Any

app = Celery('chowder')
app.config_from_object('chowder.celeryconfig')


def _clamscan(file: str, clamscan_options: Dict[str, Any] = None, timeout: int = 3600) -> Tuple[bool, str]:
    if clamscan_options is None:
        clamscan_options = {}
    if 'max-filesize' not in clamscan_options:
        clamscan_options['max-filesize'] = 0
    if 'max-scansize' not in clamscan_options:
        clamscan_options['max-scansize'] = 0

    clamscan_invocation = ['clamscan']
    clamscan_invocation.extend(
        [('--' if len(option_name) > 1 else '-') + option_name + ('=' if option_value is not None else '') +
         (str(option_value) if option_value is not None else '')
         for option_name, option_value in clamscan_options.items()])
    clamscan_invocation.append(file)

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

    # Remove filename from output
    result_output = result.stdout.replace(file + ': ', '')

    if result.returncode == 0:
        # No virus found
        return False, result_output
    elif result.returncode == 1:
        # Virus found
        return True, result_output
    else:
        raise RuntimeError(f'clamscan invocation failed with return code {result.returncode} and output: ' +
                           result_output.replace('\n', ', '))


@app.task
def scan(*, fs_url: str, file: str, timeout: int = 3600, clamscan_options: Dict[str, Any] = None) -> Tuple[bool, str]:
    with open_fs(fs_url) as input_fs, open_fs('osfs:///') as temp_fs:
        try:
            file_info = input_fs.getinfo(file)
            if file_info.is_dir:
                raise ValueError(f'Resource {file} is a directory, expecting a file.')
        except ResourceNotFound:
            raise FileNotFoundError(f'Resource {file} does not exist.')

        has_system_path = input_fs.hassyspath(file)
        if has_system_path:
            file_to_scan = input_fs.getsyspath(file)
        else:
            # We use the same temporary directory as clamscan if specified
            temp_dir = clamscan_options['tempdir'] if clamscan_options and 'tempdir' in clamscan_options else '/tmp'
            file_to_scan = '{}/{}'.format(temp_dir, uuid.uuid4().hex)
            try:
                copy_file(input_fs, file, temp_fs, file_to_scan)
            except Exception as exception:
                try:
                    temp_fs.remove(file_to_scan)
                except ResourceNotFound:
                    pass
                raise RuntimeError(f'Copying resource {file} to osfs://{file_to_scan} failed with a {type(exception).__name__} exception: {str(exception)}.'
                                  ) from None

        try:
            scan_result, scan_message = _clamscan(file_to_scan, timeout=timeout, clamscan_options=clamscan_options)
        finally:
            if not has_system_path:
                try:
                    temp_fs.remove(file_to_scan)
                except ResourceNotFound:
                    pass

    return scan_result, scan_message
