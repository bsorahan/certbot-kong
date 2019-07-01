import unittest
import mock
import json
import pkg_resources

import josepy as jose

from acme import challenges
from acme import messages

from certbot import achallenges
from certbot.compat import os
from certbot import errors
from certbot.tests import util as test_util

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
    def test_deploy_cert_old_cert_not_deleted(self, 
            request_info #type: Mock
        ):
        # GIVEN hostname with existing cert with only this SNI
        hostname = "a006.example.com"

        # WHEN deploy certificate to hostname and 
        # "delete-unused-certificates" is set to False
        setattr(self.configurator.config, 
            self.configurator.dest("delete-unused-certificates"), False)
        self.configurator.deploy_cert(
            hostname, 
            self.cert_path, 
            self.key_path, 
            self.chain_path, 
            self.fullchain_path
        )
        self.configurator.save()
        

        # THEN no api called made to delete cert004
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertTrue( 
            (
                "DELETE", 
                "/certificates/cert004",
                None
            ) not in requests
        )

    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_deploy_cert_old_cert_deleted(self, 
            request_info #type: Mock
        ):
        # GIVEN hostname with existing cert with only this SNI
        hostname = "a006.example.com"

        # WHEN deploy certificate to hostname and 
        # "delete-unused-certificates" is set to True
        setattr(self.configurator.config, 
            self.configurator.dest("delete-unused-certificates"), True)
        self.configurator.deploy_cert(
            hostname, 
            self.cert_path, 
            self.key_path, 
            self.chain_path, 
            self.fullchain_path
        )
        self.configurator.save()
        

        # THEN api called made to delete cert004
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertTrue( 
            (
                "DELETE", 
                "/certificates/cert004",
                None
            ) in requests
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
    def test_redirect_route_with_no_hosts(self, request_info):
        # GIVEN a route with HTTP which has no hosts
        domain = "nomatch.example.com"

        # WHEN redirect for a hostname
        self.configurator.enhance(
            domain,
            'redirect'
        )

        # THEN api call made to update route003 protocols to HTTPS:
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertTrue(len(requests) == 1)
        self.assertEquals(
            requests[0], 
            (
                "PATCH", 
                "/routes/route003",
                {"protocols":["https"]}
            )
        )
    
    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_no_redirect_route_with_no_hosts(self, request_info):
        # GIVEN a route with HTTP which has no hosts
        domain = "nomatch.example.com"

        # WHEN redirect for a hostname and 
        # 'redirect-route-no-host' set to False
        setattr(self.configurator.config, 
            self.configurator.dest("redirect-route-no-host"), False)
        self.configurator.enhance(
            domain,
            'redirect'
        )

        # THEN no api call made to update route003 protocols to HTTPS:
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertTrue(len(requests) == 0)

    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_redirect_route_matching_domain(self, request_info):
        # GIVEN a route with HTTP which has 
        # matching host (route002) and no hosts (route003)
        domain = "a002.example.com"

        # WHEN redirect for a hostname
        self.configurator.enhance(
            domain,
            'redirect'
        )

        # THEN api call made to update route002 and route003 
        # protocols to HTTPS:
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertCountEqual(
            requests,
            [ 
                (
                    "PATCH", 
                    "/routes/route003",
                    {"protocols":["https"]}
                ),
                (
                    "PATCH", 
                    "/routes/route002",
                    {"protocols":["https"]}
                )
            ])

    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_redirect_route_matching_wildcard_domain(self, request_info):
        # GIVEN a route with HTTP which has 
        # matching host (route001, route002) and no hosts (route003)
        domain = "*.example.com"

        # WHEN redirect for domain
        self.configurator.enhance(
            domain,
            'redirect'
        )

        # THEN api call made to update route002 and route003 
        # protocols to HTTPS:
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertCountEqual(
            requests,
            [ 
                (
                    "PATCH", 
                    "/routes/route001",
                    {"protocols":["https"]}
                ),
                (
                    "PATCH", 
                    "/routes/route002",
                    {"protocols":["https"]}
                ),
                (
                    "PATCH", 
                    "/routes/route003",
                    {"protocols":["https"]}
                )
            ]
        )
    
    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_no_redirect_route_domain_matching_some(self, request_info):
        # GIVEN a route (route002) with HTTP 
        # which has only SOME matching hosts 

        domain = "a002.example.com"

        # WHEN redirect for domain and 'redirect-route-any-host' and 
        # 'redirect-route-no-host' are set to False
        setattr(self.configurator.config, 
            self.configurator.dest("redirect-route-no-host"), False)
        setattr(self.configurator.config, 
            self.configurator.dest("redirect-route-any-host"), False)
        self.configurator.enhance(
            domain,
            'redirect'
        )

        # THEN no api call made
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertTrue(len(requests) == 0)
           
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

    @mock.patch('certbot_kong.tests.util.MockKongAdminHandler.request_info')
    def test_perform_and_cleanup(self, request_info):
        # GIVEN a HTTP authnticator challenge
        account_key = jose.JWKRSA.load(pkg_resources.resource_string(
            __name__, os.path.join('testdata', 'rsa512_key.pem')))
        token = b"m8TdO1qik4JVFtgPPurJmg"
        domain="example.com"
        achall = achallenges.KeyAuthorizationAnnotatedChallenge(
            challb=messages.ChallengeBody(
                chall=challenges.HTTP01(token=token),
                uri="https://ca.org/chall1_uri",
                status=messages.Status("pending"),
            ), domain=domain, account_key=account_key)

        expected = [
            achall.response(account_key),
        ]

        # WHEN the challenge is performed and cleaned up
        responses = self.configurator.perform([achall])
        
        self.configurator.cleanup([achall])

        # THEN a ACME challenge service is created and 
        # then cleaned up in Kong.
        calls = request_info.mock_calls
        requests = self._get_write_requests(calls)

        self.assertEqual(responses, expected)

        acme_service_requests = requests[0:3]
        cleanup_requests = requests[3:]
        
        service_id = requests[0][1][len("/services/"):]
        plugin_id = requests[1][1][len("/plugins/"):]
        route_id = requests[2][1][len("/routes/"):]

        self.assertEqual(
            acme_service_requests, 
            [
                (
                    "PUT", 
                    "/services/"+service_id,
                    {
                        "name" : "certbot-kong TEMPORARY ACME challenge",
                        "url":"http://invalid.example.com"
                    }
                ),
                (
                    "PUT", 
                    "/plugins/"+plugin_id,
                    {
                        "service":{"id":service_id},
                        "name":"request-termination",
                        "config":{
                            "status_code":200,
                            "content_type":"text/plain",
                            "body":achall.validation(achall.account_key)
                        }
                    }
                ),
                (
                    "PUT", 
                    "/routes/"+route_id,
                    {
                        "service":{"id":service_id},
                        "paths":["/.well-known/acme-challenge/"+achall.chall.encode("token")],
                        "hosts":[domain],
                        "protocols":["http"]
                    }
                )
            ]
        )

        self.assertEqual(
            cleanup_requests, 
            [
                (
                    "DELETE", 
                    "/routes/"+route_id,
                    None
                ),
                (
                    "DELETE", 
                    "/plugins/"+plugin_id,
                    None
                ),
                (
                    "DELETE", 
                    "/services/"+service_id,
                    None
                )
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