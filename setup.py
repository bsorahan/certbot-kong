from setuptools import setup
from setuptools import find_packages


setup(
    name='certbot-kong',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'mock',
        'zope.interface',
        'certbot',
        'certbot.compat',
        'certbot.plugins',
        'certbot.constants'
    ],
    entry_points={
        'certbot.plugins': [
            'kong = certbot_kong.configurator:KongConfigurator',
        ],
    },
)
