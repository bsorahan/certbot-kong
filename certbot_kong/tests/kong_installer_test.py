import unittest
import mock
import json

from certbot.compat import os
from certbot import errors


import certbot_kong.kong_admin_api as api
import certbot_kong.configurator
from certbot_kong.tests.util import KongTest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

class KongInstallerTest(KongTest):

    def test_get_all_names(self):
        names = self.configurator.get_all_names()

        self.assertEqual(names, 
            {   
                'a002.example.com', 
                'a003.test.com', 
                'test.com', 
                'a001.example.com', 
                'a004.example.com',
                'a006.example.com',
                'example.com'
            }
        )
    
    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_deploy_hostname_certificate_new(self, 
            request_info #type: Mock
        ):
        # GIVEN hostname with no existing cert or route
        hostname = "a005.example.com"

        # WHEN deploy certificate to hostname
        self.configurator.deploy_cert(
            hostname, 
            self.cert_path, 
            self.key_path, 
            self.chain_path, 
            self.fullchain_path
        )
        self.configurator.save()
        

        # THEN api call made to create the cert and 
        # create the sni associated to the cert
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        cert_id = requests[0][1][len("/certificates/"):]
        self.assertEquals(
            requests[0], 
            (
                "PUT", 
                "/certificates/"+cert_id,
                {"key":self.key_str,"cert":self.fullchain_str}
            )
        )

        self.assertCountEqual(
            requests[1:], 
            [
                (
                    "POST", 
                    "/snis",
                    {
                        "name":hostname,
                        "certificate": {"id":cert_id}
                    }
                )
            ]
        )

    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_deploy_hostname_certificate_update(self, request_info):
        # GIVEN hostname which has a an existing certificate
        hostname = "a002.example.com"

        # WHEN deploy certificate to hostname
        self.configurator.deploy_cert(
            hostname, 
            self.cert_path, 
            self.key_path, 
            self.chain_path, 
            self.fullchain_path
        )
        self.configurator.save()

        # THEN api call made to:
        # 1. create the new cert 
        # 2. Update SNI with the new cert:
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        cert_id = requests[0][1][len("/certificates/"):]
        self.assertEquals(
            requests[0], 
            (
                "PUT", 
                "/certificates/"+cert_id,
                {"key":self.key_str,"cert":self.fullchain_str}
            )
        )

        self.assertCountEqual(
            requests[1:], 
            [
                (
                    "PATCH", 
                    "/snis/a002.example.com",
                    {
                        "name":"a002.example.com",
                        "certificate": {"id":cert_id}
                    }
                )
            ]
        )


    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_deploy_wildcard_hostname_certificate(self,
        request_info
        ):
        # GIVEN hostname with no existing cert or route
        hostname = "*.example.com"

        # WHEN deploy certificate to hostname
        self.configurator.deploy_cert(
            hostname, 
            self.cert_path, 
            self.key_path, 
            self.chain_path, 
            self.fullchain_path
        )
        self.configurator.save()
      
        
        # THEN api call made to:
        # 1. create the new cert 
        # 2. SNIs associated to cert:
        #  a. update SNIs a001.example.com, a002.example.com, a006.example.com
        #  b. create SNI a004.example.com
        # 3. cert for a004.example.com deleted as no longer referenced
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        cert_id = requests[0][1][len("/certificates/"):]
        self.assertEquals(
            requests[0], 
            (
                "PUT", 
                "/certificates/"+cert_id,
                {"key":self.key_str,"cert":self.fullchain_str}
            )
        )

        self.assertCountEqual(
            requests[1:], 
            [
                (
                    "PATCH", 
                    "/snis/a001.example.com",
                    {
                        "name":"a001.example.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "PATCH", 
                    "/snis/a002.example.com",
                    {
                        "name":"a002.example.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "PATCH", 
                    "/snis/a006.example.com",
                    {
                        "name":"a006.example.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "POST", 
                    "/snis",
                    {
                        "name":"a004.example.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "DELETE", 
                    "/certificates/cert004",
                    None
                ),
            ]
        )

    @mock.patch('certbot_kong.tests.util.configurator.KongAdminApi.create_sni')
    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_deploy_hostname_undo_changes_after_error(self,
        request_info,
        create_sni
        ):
        # GIVEN hostname with no existing cert or route
        hostname = "*.example.com"

        # WHEN deploy certificate to hostname and error encountered creating SNI
        create_sni.side_effect = api.ApiError("foo")
        self.configurator.deploy_cert(
            hostname, 
            self.cert_path, 
            self.key_path, 
            self.chain_path, 
            self.fullchain_path
        )   
        
        # THEN:
        # 1. error encountered creating sni a004.example.com
        # 2. UNDO previous operations and assert that the
        # newly created cert has been deleted

        self.assertRaises(errors.PluginError, self.configurator.save)   
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        cert_id = requests[0][1][len("/certificates/"):]

        # assert last request was deleting the newly created cert
        self.assertEquals(
            requests[-1],
            (
                "DELETE", 
                "/certificates/"+cert_id,
                None
            )
        )


    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_deploy_many_hostnames_certificate(self, request_info): 
        # GIVEN many hostnames 
        hostnames = ["*.example.com", "a003.test.com", "test.com"]

        # WHEN deploy
        for hostname in hostnames:
            self.configurator.deploy_cert(
                hostname, 
                self.cert_path, 
                self.key_path, 
                self.chain_path, 
                self.fullchain_path
            )
        self.configurator.save()

        # THEN api call made to:
        # 1. create the new cert 
        # 2. SNIs associated to cert:
        #   a. update a001.example.com, 
        #       a002.example.com, a006.example.com, a003.test.com, test.com
        #   b. create a004.example.com
        # 3. cert001, cert002, cert004 deleted as no longer referenced
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        cert_id = requests[0][1][len("/certificates/"):]
        self.assertEquals(
            requests[0], 
            (
                "PUT", 
                "/certificates/"+cert_id,
                {"key":self.key_str,"cert":self.fullchain_str}
            )
        )

        self.assertCountEqual(
            requests[1:], 
            [
                (
                    "PATCH", 
                    "/snis/a001.example.com",
                    {
                        "name":"a001.example.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "PATCH", 
                    "/snis/a002.example.com",
                    {
                        "name":"a002.example.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "PATCH", 
                    "/snis/a006.example.com",
                    {
                        "name":"a006.example.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "PATCH", 
                    "/snis/test.com",
                    {
                        "name":"test.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "PATCH", 
                    "/snis/a003.test.com",
                    {
                        "name":"a003.test.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "POST", 
                    "/snis",
                    {
                        "name":"a004.example.com",
                        "certificate": {"id":cert_id}
                    }
                ),
                (
                    "DELETE", 
                    "/certificates/cert001",
                    None
                ),
                (
                    "DELETE", 
                    "/certificates/cert002",
                    None
                ),
                (
                    "DELETE", 
                    "/certificates/cert004",
                    None
                ),
            ]
        )

    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_deploy_existing_certificate_for_sni(self, request_info):
        # GIVEN exisiting certificate
        hostname = "a001.example.com"
        key_path = os.path.join(THIS_DIR, 
            "testdata/key_file_reuse.txt")
        fullchain_path = os.path.join(THIS_DIR, 
            "testdata/fullchain_file_reuse.txt")

        # WHEN deploy certificate 
        self.configurator.deploy_cert(
            hostname, 
            self.cert_path, 
            key_path, 
            self.chain_path, 
            fullchain_path
        )
        self.configurator.save()

        # THEN no new certificate is created and SNIs aren't updated
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertEquals(len(requests),0)

    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_rollback(self,
        request_info
        ):
        # GIVEN hostname with no existing cert or route
        hostname = "*.example.com"
        self.configurator.deploy_cert(
            hostname, 
            self.cert_path, 
            self.key_path, 
            self.chain_path, 
            self.fullchain_path
        )
        self.configurator.save()
      
        # WHEN rollback
        self.configurator.rollback_checkpoints()
        
        # THEN rollback request api calls made:
        # 1. recreate cert004 
        # 2. SNIs associated back to cert:
        #   a. update a001.example.com, a002.example.com, a006.example.com
        # 3. delete a004.example.com (didn't previously exist)
        # 3. delete newly created cert
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        cert_id = requests[0][1][len("/certificates/"):]
        rollback_requests = requests[6:]
        self.assertCountEqual(
            rollback_requests, 
            [
                (
                    "PUT", 
                    "/certificates/cert004",
                    {
                        "key": "-----BEGIN PRIVATE KEY-----\n.8."
                            "\n-----END PRIVATE KEY-----",
                        "cert": "-----BEGIN CERTIFICATE-----\n.7."
                            "\n-----END CERTIFICATE-----"
                    }
                ),
                (
                    "PATCH", 
                    "/snis/a001.example.com",
                    {
                        "name":"a001.example.com",
                        "certificate": {"id":"cert001"}
                    }
                ),
                (
                    "PATCH", 
                    "/snis/a002.example.com",
                    {
                        "name":"a002.example.com",
                        "certificate": {"id":"cert002"}
                    }
                ),
                (
                    "PATCH", 
                    "/snis/a006.example.com",
                    {
                        "name":"a006.example.com",
                        "certificate": {"id":"cert004"}
                    }
                ),
                (
                    "DELETE", 
                    "/snis/a004.example.com",
                    None
                ),
                (
                    "DELETE", 
                    "/certificates/"+cert_id,
                    None
                )
            ]
        )

        # assert deletion of new cert was the last request
        self.assertEquals(
            rollback_requests[-1], 
           (
                "DELETE", 
                "/certificates/"+cert_id,
                None
            )
        )

        # assert recreation of cert004 is before sni a006.example.com update
        recreation_idx = rollback_requests.index((
            "PUT", 
            "/certificates/cert004",
            {
                "key": "-----BEGIN PRIVATE KEY-----\n.8.\n-----END PRIVATE KEY-----",
                "cert": "-----BEGIN CERTIFICATE-----\n.7.\n-----END CERTIFICATE-----"
            }
        ))

        sni_update_idx = rollback_requests.index((
            "PATCH", 
            "/snis/a006.example.com",
            {
                "name":"a006.example.com",
                "certificate": {"id":"cert004"}
            }
        ))

        self.assertTrue(recreation_idx < sni_update_idx)


    def _get_write_requests(self, calls):
        """ Helper function to clean and remove GET requests from calls.
        """
        requests = []
        for c in calls:
            if c.args[0] != "GET":
                body = None
                if c.args[2]:
                    body = json.loads(c.args[2].decode('utf-8'))
                requests.append((c.args[0], c.args[1], body))
        return requests



if __name__ == '__main__':
    unittest.main()