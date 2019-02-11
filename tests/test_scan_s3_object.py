import unittest
from copy import deepcopy
from typing import Dict

import boto3
from botocore.client import Config as BotoCoreClientConfig
from botocore.handlers import set_list_objects_encoding_type_url
from celery import Celery

app = Celery('test')
app.config_from_object('chowder.celeryconfig')
app.conf.update({'broker_url': 'amqp://guest:guest@localhost:5672'})

class TestScanS3Object(unittest.TestCase):
    RESOURCE_CONFIG_LOCAL = {
        'aws_access_key_id': 'minio',
        'aws_secret_access_key': 'minio123',
        'endpoint_url': 'http://localhost:9000',
        # 'region': ''
        'config': {
            's3': {'addressing_style': 'path'},
            # 'signature_version': 's3', # 's3' is v2 and  's3v4' is v4
        }
    }

    RESOURCE_CONFIG = {
        'aws_access_key_id': 'minio',
        'aws_secret_access_key': 'minio123',
        'endpoint_url': 'http://minio:9000',
        # 'region': ''
        'config': {
            's3': {'addressing_style': 'path'},
            # 'signature_version': 's3', # 's3' is v2 and  's3v4' is v4
        }
    }

    @staticmethod
    def create_s3_resource(resource_config: Dict, disable_encoding_type: bool):
        my_resource_config = deepcopy(resource_config)
        my_resource_config['config'] = BotoCoreClientConfig(**my_resource_config['config'])

        session = boto3.session.Session()
        if disable_encoding_type:
            session.events.unregister('before-parameter-build.s3.ListObjects', set_list_objects_encoding_type_url)

        return session.resource('s3', **my_resource_config)

    @classmethod
    def setUpClass(cls):
        s3_resource = cls.create_s3_resource(cls.RESOURCE_CONFIG_LOCAL, disable_encoding_type=False)
        try:
            s3_resource.Bucket('chowder').objects.all().delete()
            s3_resource.Bucket('chowder').delete()
        except Exception:
            pass
        s3_resource.create_bucket(Bucket='chowder')
        s3_resource.Object('chowder', 'test-1').upload_file('LICENSE.md')
        s3_resource.Object('chowder', 'test-2').upload_file('eicar.com')

    @classmethod
    def tearDownClass(cls):
        s3_resource = cls.create_s3_resource(cls.RESOURCE_CONFIG_LOCAL, disable_encoding_type=False)
        s3_resource.Bucket('chowder').objects.all().delete()
        s3_resource.Bucket('chowder').delete()

    def test_scan_s3_object_clean(self):
        result, output = app.send_task('chowder.tasks.scan_s3_object', args=(self.RESOURCE_CONFIG, 'chowder', 'test-1')).get()
        print('Scan result {}, output {}.'.format(result, output))
        self.assertFalse(result)
        self.assertRegex(output, r'OK')

    def test_scan_s3_object_infected(self):
        result, output = app.send_task('chowder.tasks.scan_s3_object', args=(self.RESOURCE_CONFIG, 'chowder', 'test-2')).get()
        print('Scan result {}, output {}.'.format(result, output))
        self.assertTrue(result)
        self.assertRegex(output, r'Eicar-Test-Signature FOUND')

if __name__ == '__main__':
    unittest.main()


