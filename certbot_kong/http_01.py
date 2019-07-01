"""A class that performs HTTP-01 challenges for Kong"""

import logging

from acme import challenges
from acme.magic_typing import List # pylint: disable=unused-import, no-name-in-module

from certbot import errors
from certbot.compat import os
from certbot.plugins import common

logger = logging.getLogger(__name__)

class KongHttp01(common.ChallengePerformer):
    """HTTP-01 authenticator for Kong
    :ivar configurator: NginxConfigurator object
    :type configurator: :class:`~nginx.configurator.NginxConfigurator`
    :ivar list achalls: Annotated
        class:`~certbot.achallenges.KeyAuthorizationAnnotatedChallenge`
        challenges
    :ivar indices: Holds the indices of challenges from a larger array
        so the user of the class doesn't have to.
    """

    def __init__(self, configurator):
        super(KongHttp01, self).__init__(configurator)


    def perform(self):
        """Perform a challenge on Kong.
        :returns: list of :class:`certbot.acme.challenges.HTTP01Response`
        :rtype: list
        """
        if not self.achalls:
            return []

        responses = [x.response(x.account_key) for x in self.achalls]

        for achall in self.achalls:
            self.configurator.invoker.create_http01_challenge_service(
                achall.domain,
                achall.validation(achall.account_key),
                self._get_validation_path(achall)
            )

        # Save reversible changes
        self.configurator.save("HTTP Challenge", True)

        return responses

    def _get_validation_path(self, achall):
        return "/"+challenges.HTTP01.URI_ROOT_PATH+"/"+achall.chall.encode("token")