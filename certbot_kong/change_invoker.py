import logging
import uuid
import collections

import certbot_kong.kong_admin_api as api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KongChangeInvokerError(Exception):
    """Exception when there is a kong config error"""
    pass

class KongChangeInvoker(object):

    def __init__(self, 
            api #type: api
            ):
        self._api = api
        self._queued_changes = [] #type: List[Change]
        self._executed_changes = collections.deque() #type: Deque[Change]
        self.load_config()

    @property
    def routes(self):
        return self._routes

    @property
    def certs(self):
        return self._certs

    def clear_changes(self):
        self._queued_changes = []
        self._executed_changes = collections.deque()


    def load_config(self):
        """Retrieves the current kong route and certificate configuration details.
        """
        if len(self._queued_changes) > 0:
            raise KongChangeInvokerError(
                'Unable to load config while changes are queued') 
        self._certs = self._api.list_certificates()
        self._routes = self._api.list_routes()

    def set_sni_cert(self, sni, fullchain_str, key_str, 
            delete_unused_certs=True):
        """Sets a SNI with a certificate.

        If the SNI does not exist then it will be created.
        If the certificate does not exist then it will be created.
        If the certificate previously used by the SNI no longer references 
        any SNIs then it is deleted.

        All changes are queued, operations on Kong Admin API to commit the 
        changes will perfromed by apply_changes()

        """
        cert = self._get_cert(fullchain_str, key_str)
        old_cert, old_cert_index = self._get_sni_cert(sni)
        cert_id = None

        if cert is None:
            # Create certificate
            cert_id = str(uuid.uuid4())
            cert = {
                "id":cert_id,
                "cert":fullchain_str,
                "key":key_str,
                "snis":[]
            }
            self._certs.append(cert)
            logger.info("Adding certificate %s" 
                % cert_id) 
            self._queue_change(
                AddCertificate(cert_id, 
                    CertificateData(fullchain_str,key_str)))

        else:
            cert_id = cert['id']
            

        if old_cert is None:
            # create a new SNI
            logger.info("Creating SNI %s with certificate %s"
                % (sni, cert_id))
            self._queue_change(CreateSni(sni, cert_id))

        else:
            old_cert_id=old_cert['id']

            if old_cert_id == cert_id:
                logger.info(("SNI %s already using certificate %s. "
                    "No action required")
                    % (sni, cert_id))
            else:
                # Update SNI with the newly created certificate
                logger.info("Updating SNI %s certificate from %s to %s"
                    % (sni, old_cert_id, cert_id))
                self._queue_change(
                    UpdateSniCertificate(sni, cert_id, old_cert_id))

                # update cert snis reference
                old_snis = old_cert.get('snis',[])
                old_snis.remove(sni)
                if len(old_snis) <= 0 and delete_unused_certs:
                    # Certificate no longer references any snis and 
                    # can be deleted
                    del self._certs[old_cert_index]
                    logger.info("Deleting certificate %s "
                        "as no SNIs are using it"
                        % old_cert_id)
                    self._queue_change(DeleteCertificate(old_cert_id, 
                        CertificateData(
                            old_cert.get('cert'),old_cert.get('key'))))
        
        # Update cert with reference to sni
        snis = cert.get('snis',[])
        snis.append(sni)
        cert['snis'] = list(set(snis))

    def _get_cert(self, fullchain_str, key_str):
        """helper function to find the certificate matching the 
        fullchain and key
        """
        for c in self._certs:
            if(fullchain_str == c.get('cert') and key_str == c.get('key')):
                return c
        return None

    def _get_sni_cert(self, sni):
        """helper function to find the certificate used by the SNI.
        """
        i=0
        for c in self._certs:
            if sni in c.get('snis',[]):
                return c, i
            i += 1
        return None, -1

    def redirect_route(self, route_id):
        route = self._get_route(route_id)

        if not route:
            raise KongChangeInvokerError("Unable to redirect route for %s "
            "as there is no matching route" % route_id)

        old_protocols = route.get('protocols',[])
        redirect_protocols = ['https']
        logger.info("Updating Route %s protocols from %s to %s"
            % (route_id, str(old_protocols), str(redirect_protocols)))
        self._queue_change(UpdateRouteProtocols(route_id, 
            redirect_protocols, old_protocols))
        route['protocols'] = redirect_protocols

    def create_http01_challenge_service(self, 
            domain, validation, validation_path):
        service_id = str(uuid.uuid4())
        plugin_id = str(uuid.uuid4())
        route_id = str(uuid.uuid4())
        logger.info("Adding http01 challenge service %s "
            "(with request-termination plugin %s and route %s)" 
                % (service_id,plugin_id,route_id)) 
        self._queue_change(
                CreateService(service_id, 
                    {
                        "name" : "certbot-kong TEMPORARY ACME challenge",
                        "url":"http://invalid.example.com"
                    }
                ))
        self._queue_change(
                CreatePlugin(plugin_id, 
                    {
                        "service":{"id":service_id},
                        "name":"request-termination",
                        "config":{
                            "status_code":200,
                            "content_type":"text/plain",
                            "body":validation
                        }
                    }
                ))
        
        self._queue_change(
                CreateRoute(route_id, 
                    {
                        "service":{"id":service_id},
                        "paths":[validation_path],
                        "hosts":[domain],
                        "protocols":["http"]
                    }
                ))
            
            
    def _get_route(self, route_id):
        for r in self._routes:
            if r['id']==route_id:
                return r
        return None

            
    def get_changes_details(self):
        details = []

        for change in self._queued_changes:
            details.append(change.get_details())

        return details

    def _queue_change(self, Change, #type: Change
            ):
        self._queued_changes.append(Change)

    def apply_changes(self):
        """ Apply changes.
        Iterate through the changes and execute() each of them
        """
        for change in self._queued_changes:
            try:
                change.execute(self._api)
                self._executed_changes.append(change)
            except:
                # revert changes
                self.undo_changes()
                raise 
        self._queued_changes=[]

    def undo_changes(self):
        """ undo changes
        """
        while self._executed_changes:
            change = self._executed_changes.pop()

            try:
                change.undo(self._api)
            except:
                UndoChangesError(
                    change, 
                    self._executed_changes, 
                    "Unable to undo changes."
                    " Configuration may be in an inconsitant state")
            
        


class Change(object):
    """Change interface"""

    def execute(self, api #type: api
            ):
        raise NotImplementedError
    
    def undo(self, api #type: api
            ):
        raise NotImplementedError

    def get_details(self):
        raise NotImplementedError

class AddCertificate(Change):
    """Change to add a new certificate to kong."""
    
    def __init__(self, 
        certificate_id,
        certificate_data #type: CertificateData
            ):
        self._certificate_id = certificate_id
        self._certificate_data = certificate_data

    @property
    def certificate_id(self):
        return self._certificate_id

    def execute(self, api #type: api
            ):
        api.update_or_create_certificate(
            self._certificate_id,
            self._certificate_data.cert, 
            self._certificate_data.key, 
            self._certificate_data.snis
        )

    def undo(self, api #type: api
            ):
        api.delete_certificate(self._certificate_id)

    def get_details(self):
        return "Add certificate %s" % self._certificate_id

class DeleteCertificate(Change):
    """Change to delete a certificate in kong."""
    
    def __init__(self, certificate_id, certificate_data #type: CertificateData
            ):
        self._certificate_id = certificate_id
        self._certificate_data = certificate_data

    def execute(self, api #type: api
            ):
        api.delete_certificate(self._certificate_id)
    
    def undo(self, api #type: api
            ):
        
        api.update_or_create_certificate(
            self._certificate_id,
            self._certificate_data.cert, 
            self._certificate_data.key, 
            self._certificate_data.snis
        )

    def get_details(self):
        return "Delete certificate %s" % self._certificate_id

class UpdateCertificate(Change):
    """Change to update an existing certificate to kong."""
    def __init__(self, certificate_id, #type str
            certificate_data,  #type: CertificateData
            old_certificate_data #type: CertificateData
            ):
        self._certificate_id = certificate_id
        self._certificate_data = certificate_data
        self._old_certificate_data = old_certificate_data

    def execute(self, api):
        api.update_certificate(
            self._certificate_id,
            self._certificate_data.cert, 
            self._certificate_data.key, 
            self._certificate_data.snis
        )
    
    def undo(self, api):
        api.update_certificate(
            self._certificate_id,
            self._old_certificate_data.cert, 
            self._old_certificate_data.key, 
            self._old_certificate_data.snis
        )

    def get_details(self):
        return "Update certificate %s" % self._certificate_id

class UpdateRouteProtocols(Change):
    """Change to update an existing route protocols to kong."""
    def __init__(self, route_id, #type str
            protocols, #type: list[str]
            old_protocols #type: list[str]
            ):
        self.route_id = route_id
        self.protocols = protocols
        self.old_protocols = old_protocols

    def execute(self, api):
        api.update_route_protocols(
            self.route_id,
            self.protocols
        )
    
    def undo(self, api):
       api.update_route_protocols(
            self.route_id,
            self.old_protocols
        )
    
    def get_details(self):
        return "Update route protocol %s" % self.route_id

class UpdateSniCertificate(Change):
    """Change to update an existing sni with a certificate."""
    def __init__(self, 
            sni, # type str
            cert_id, #type str
            old_cert_id #type str
            ):
        self._sni = sni
        self._cert_id = cert_id
        self._old_cert_id = old_cert_id

    def execute(self, api):
        api.update_sni(
            self._sni,
            self._cert_id
        )
    
    def undo(self, api):
       api.update_sni(
            self._sni,
            self._old_cert_id
        )

    def get_details(self):
        return "Update SNI %s" % self._sni

class CreateSni(Change):
    """Change to update an existing sni with a certificate."""
    def __init__(self, 
            sni, # type str
            cert_id #type str
            ):
        self._sni = sni
        self._cert_id = cert_id

    def execute(self, api):
        api.create_sni(
            self._sni,
            self._cert_id
        )
    
    def undo(self, api):
       api.delete_sni(
            self._sni
        )

    def get_details(self):
        return "Add SNI %s" % self._sni

class CreateService(Change):
    """Change to create a service."""
    def __init__(self, 
            service_id, # type str
            data #type Dict
            ):
        self._service_id = service_id
        self._data = data

    def execute(self, api):
        api.update_or_create_service(self._service_id, self._data)
    
    def undo(self, api):
       api.delete_service(
            self._service_id
        )

    def get_details(self):
        return "Add Service %s" % self._service_id

class CreatePlugin(Change):
    """Change to create a plugin."""
    def __init__(self, 
            plugin_id, # type str
            data #type Dict
            ):
        self._plugin_id = plugin_id
        self._data = data

    def execute(self, api):
        api.update_or_create_plugin(self._plugin_id, self._data)
    
    def undo(self, api):
       api.delete_plugin(
            self._plugin_id
        )

    def get_details(self):
        return "Add Plugin %s" % self._plugin_id


class CreateRoute(Change):
    """Change to create a route."""
    def __init__(self, 
            route_id, # type str
            data #type Dict
            ):
        self._route_id = route_id
        self._data = data

    def execute(self, api):
        api.update_or_create_route(self._route_id, self._data)
    
    def undo(self, api):
       api.delete_route(
            self._route_id
        )

    def get_details(self):
        return "Add Route %s" % self._route_id

class CertificateData(object):
    def __init__(self, cert, key, snis=None):
        self.cert = cert
        self.key = key
        self.snis = snis


class UndoChangesError(Exception):
    """ Rasied when an error is encountered while undoing changes"""
    def __init__(self, failed_change, remaining_changes, message):
        self.failed_change = failed_change
        self.remaining_changes = remaining_changes
        self.message = message

class ApplyChangesError(Exception):
    """Raised when an error occurs while applying changes"""
    pass