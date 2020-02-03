""" Module wrapping Kong Admin API REST operations """
import logging
import requests


_default_kong_admin_url = "http://localhost:8001"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Exception for api errors"""

class NotFound(Exception):
    """Exception for api errors"""


class KongAdminApi():
    """ Kong Admin API wrapper """

    def __init__(self, url=_default_kong_admin_url):
        self.url = url

    def list_routes(self):
        """ list the routes (GET /routes) """
        r = requests.get(self.url + "/routes")
        if r.status_code != 200:
            raise ApiError('Unable to list routes: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()['data']

    def list_certificates(self):
        """ list the certificates (GET /certificates) """
        r = requests.get(self.url + "/certificates")
        if r.status_code != 200:
            raise ApiError('Unable to list certificates: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()['data']

    def update_certificate(self, certificate_id, cert, key, snis=None):
        """ update the certificate (PATCH /certificates/{cert}) """
        data = {
                "cert": cert,
                "key": key,
                "snis": snis
            }
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.patch(self.url+"/certificates/"+certificate_id, json=data)

        if r.status_code != 200:
            raise ApiError('Unable to update certificate: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def update_or_create_certificate(self, certificate_id, cert, key,
            snis=None
            ):
        """ update or create the certificate (PUT /certificates/{cert}) """
        data = {
                "cert": cert,
                "key": key,
                "snis": snis
            }
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.put(self.url+"/certificates/"+certificate_id, json=data)

        if r.status_code not in [200, 201]:
            raise ApiError('Unable to update or create certificate: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def add_certificate(self, cert, key, snis):
        """ create the certificate (POST /certificates/{cert}) """
        data = {
                "cert": cert,
                "key": key,
                "snis": snis
            }
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.post(self.url+"/certificates", json=data)

        if r.status_code != 201:
            raise ApiError('Unable to add certificate: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def delete_certificate(self, certificate_id):
        """ delete the certificate (DELETE /certificates/{cert}) """
        r = requests.delete(self.url+"/certificates/"+certificate_id)

        if r.status_code != 204:
            raise ApiError('Unable to delete certificate: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))

    def create_sni(self, sni, certificate_id):
        """ create the sni (POST /snis/{sni}) """
        data = {
                "name": sni,
                "certificate": {"id": certificate_id}
            }
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.post(self.url + "/snis", json=data)

        if r.status_code != 201:
            raise ApiError('Unable to add sni: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def update_sni(self, sni, certificate_id):
        """ update the sni (PATCH /snis/{sni}) """
        data = {
                "name": sni,
                "certificate": {"id": certificate_id}
            }
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.patch(self.url+"/snis/"+sni, json=data)

        if r.status_code != 200:
            raise ApiError('Unable to update sni: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def delete_sni(self, sni):
        """ delete the sni (DELETE /snis/{sni}) """
        r = requests.delete(self.url+"/snis/"+sni)

        if r.status_code != 204:
            raise ApiError('Unable to delete sni: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))

    def update_route_protocols(self, route_id, protocols):
        """ delete the route (PATCH /routes/{route}) """
        data = {
                "protocols": protocols
            }
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.patch(self.url+"/routes/"+route_id, json=data)

        if r.status_code != 200:
            raise ApiError('Unable to update route: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def update_or_create_plugin(self, plugin_id, data):
        """ update or create the plugin (PUT /plugins/{plugin}) """
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.put(self.url+"/plugins/"+plugin_id, json=data)

        if r.status_code not in [200, 201]:
            raise ApiError('Unable to update or create plugin: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def delete_plugin(self, plugin_id):
        """ delete the plugin (DELETE /plugins/{plugin}) """
        r = requests.delete(self.url+"/plugins/"+plugin_id)

        if r.status_code != 204:
            raise ApiError('Unable to delete plugin: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))

    def update_or_create_service(self, service_id, data):
        """ update or create the service (PUT /services/{service}) """
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.put(self.url+"/services/"+service_id, json=data)

        if r.status_code not in [200, 201]:
            raise ApiError('Unable to update or create service: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def delete_service(self, service_id):
        """ delete the service (DELETE /services/{service}) """
        r = requests.delete(self.url+"/services/"+service_id)

        if r.status_code != 204:
            raise ApiError('Unable to delete service: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))

    def update_or_create_route(self, route_id, data):
        """ update or create the route (PUT /routes/{route}) """
        data = {k: v for k, v in data.items() if v is not None}
        r = requests.put(self.url+"/routes/"+route_id, json=data)

        if r.status_code not in [200, 201]:
            raise ApiError('Unable to update or create route: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def delete_route(self, route_id):
        """ delete the route (DELETE /routes/{route}) """
        r = requests.delete(self.url+"/routes/"+route_id)

        if r.status_code != 204:
            raise ApiError('Unable to delete route: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
