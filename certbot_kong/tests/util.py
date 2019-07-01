   
"""Common utilities for certbot_kong."""
import shutil
import sys
import unittest

import josepy as jose
import mock
import zope.component

from certbot.compat import os
from certbot.display import util as display_util
from certbot.plugins import common
from certbot.tests import util as test_util

from certbot_kong import configurator
from certbot_kong.tests.mock_http_server import MockHttpServer
from certbot_kong.tests.mock_kong_admin_handler import MockKongAdminHandler


THIS_DIR = os.path.dirname(os.path.abspath(__file__))

class KongTest(unittest.TestCase):  # pylint: disable=too-few-public-methods

    def setUp(self):
        super(KongTest, self).setUp()

        self.temp_dir, self.config_dir, self.work_dir = common.dir_setup(
            test_dir="test_kong",
            pkg="certbot_kong.tests")

        self.config_path = os.path.join(self.temp_dir, "test_kong")

        self.server = MockHttpServer(handler=MockKongAdminHandler)
        self.server.start()

        self.configurator = get_kong_configurator(self.server.url, self.config_path,
                                              self.config_dir, self.work_dir)

        self.cert_path = os.path.join(THIS_DIR, 
            "testdata/cert_file.txt")
        self.key_path = os.path.join(THIS_DIR, 
            "testdata/key_file.txt")
        self.chain_path = os.path.join(THIS_DIR, 
            "testdata/chain_file.txt")
        self.fullchain_path = os.path.join(THIS_DIR, 
            "testdata/fullchain_file.txt")

        self.fullchain_path = os.path.join(THIS_DIR, 
            "testdata/fullchain_file.txt")

        with open(self.key_path, 'r') as file:
            self.key_str = file.read()

        with open(self.fullchain_path, 'r') as file:
            self.fullchain_str = file.read()

        

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        shutil.rmtree(self.config_dir)
        shutil.rmtree(self.work_dir)


def get_kong_configurator(  # pylint: disable=too-many-arguments, too-many-locals
        kong_admin_url,
        config_path,
        config_dir, 
        work_dir):
    """Create a Kong Configurator with the specified options.
    :param conf: Function that returns binary paths. self.conf in Configurator
    """
    backups = os.path.join(work_dir, "backups")

    
    config = configurator.KongConfigurator(
        config=mock.MagicMock(
            kong_admin_url = kong_admin_url,
            backup_dir=backups,
            config_dir=config_dir,
            http01_port=80,
            temp_checkpoint_dir=os.path.join(work_dir, "temp_checkpoints"),
            in_progress_dir=os.path.join(backups, "IN_PROGRESS"),
            work_dir=work_dir, 
            strict_permissions=False
        ),
        name="kong"
    )

    config.prepare()

    return config
