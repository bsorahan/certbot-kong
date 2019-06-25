import unittest
import mock
import json

from certbot.compat import os


import certbot_kong.kong_admin_api as api
import certbot_kong.configurator
from certbot_kong.tests.util import KongTest




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
        self.configurator.deploy_certs(
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
        # GIVEN hostname which has a certificate
        hostname = "a002.example.com"

        # WHEN deploy certificate to hostname
        self.configurator.deploy_certs(
            hostname, 
            self.cert_path, 
            self.key_path, 
            self.chain_path, 
            self.fullchain_path
        )
        self.configurator.save()

        # THEN api call made to:
        # 1. create the new cert 
        # 2. Update SNI with the new cert cert:
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
        self.configurator.deploy_certs(
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
        #   a. update a001.example.com, a002.example.com, a006.example.com
        #   b. create a004.example.com
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

        
    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_deploy_many_hostnames_certificate(self, request_info): 
        # GIVEN many hostnames 
        hostnames = ["*.example.com", "a003.test.com", "test.com"]

        # WHEN deploy
        for hostname in hostnames:
            self.configurator.deploy_certs(
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