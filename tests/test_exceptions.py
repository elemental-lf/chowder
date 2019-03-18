import unittest

from celery import Celery
from fs import open_fs
from fs.copy import copy_file
from fs.errors import ResourceNotFound

app = Celery('test_scan')
app.config_from_object('chowder.celeryconfig')
app.conf.update({'broker_url': 'amqp://guest:guest@localhost:5672'})

scan = app.signature('chowder.tasks.scan')


class TestScanS3Object(unittest.TestCase):
    BUCKET_NAME_INPUT = 'chowder'

    FS_URL_HOST = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://localhost:9000'
    FS_URL = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://minio:9000'

    TEST_FILE = 'test-file'
    NON_EXISTENT_FILE = 'file-not-found'

    @classmethod
    def tearDownClass(cls):
        try:
            with open_fs(cls.FS_URL_HOST) as fs:
                fs.remove(cls.TEST_FILE)
        except ResourceNotFound:
            pass

    def test_file_not_found(self):
        self.assertRaises(FileNotFoundError, lambda: scan.delay(fs_url=self.FS_URL, file=self.NON_EXISTENT_FILE).get())

    def test_invalid_clamscan_option(self):
        with open_fs(self.FS_URL_HOST) as fs:
            fs.writebytes(self.TEST_FILE, b'Hallo Du da!')
        self.assertRaises(
            RuntimeError, lambda: scan.delay(
                fs_url=self.FS_URL, file=self.TEST_FILE, clamscan_options={
                    'invalid-option': 10
                }).get())


if __name__ == '__main__':
    unittest.main()
