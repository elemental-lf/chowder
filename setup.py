try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.rstrip() for line in f]

setup(
    name='celery_chowder',
    version='0.1.0',
    description='All-in-one Docker image of ClamAV with Celery worker, REST API and clamd',
    url='http://github.com/elemental-lf/chowder',
    author='Lars Fenneberg',
    author_email='lf@elemental.net',
    license='MIT',
    packages=['celery_chowder'],
    zip_safe=False,
    python_requires='~=3.6',
    install_requires=requirements,
)
