from setuptools import setup


setup(
    name='certbot-kong-installer',
    package='certbot_kong/kong_installer.py',
    install_requires=[
        'mock',
        'certbot',
        'zope.interface',
    ],
    entry_points={
        'certbot.plugins': [
            'kong = certbot_kong.kong_installer:Installer',
        ],
    },
)