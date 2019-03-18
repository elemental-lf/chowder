import unittest

from celery import Celery
from fs import open_fs
from fs.copy import copy_file
from fs.errors import ResourceNotFound

app = Celery('test_scan')
app.config_from_object('chowder.celeryconfig')
app.conf.update({'broker_url': 'amqp://guest:guest@localhost:5672'})

scan = app.signature('chowder.tasks.scan')


class TestScan(unittest.TestCase):
    BUCKET_NAME_INPUT = 'chowder'

    FS_URL_HOST = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://localhost:9000'
    FS_URL = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://minio:9000'

    TEST_FILE = 'test-file'

    @classmethod
    def tearDownClass(cls):
        try:
            with open_fs(cls.FS_URL_HOST) as fs:
                fs.remove(cls.TEST_FILE)
        except ResourceNotFound:
            pass

    def _test_scan(self, local_file, expected_scan_result, expected_scan_message):
        with open_fs('osfs://..') as source_fs, open_fs(self.FS_URL_HOST) as destination_fs:
            copy_file(source_fs, local_file, destination_fs, self.TEST_FILE)

        scan_result, scan_message = scan.delay(fs_url=self.FS_URL, file=self.TEST_FILE).get()

        print('Scan result {}, message {}.'.format(scan_result, scan_message))
        self.assertEqual(scan_result, expected_scan_result)
        self.assertRegex(scan_message, expected_scan_message)

    def test_scan_clean(self):
        self._test_scan('LICENSE.md', False, r'OK')

    def test_scan_infected(self):
        self._test_scan('eicar.com', True, r'Eicar-Test-Signature FOUND')


if __name__ == '__main__':
    unittest.main()
