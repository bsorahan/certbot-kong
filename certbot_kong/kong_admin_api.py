import requests
import logging

_default_kong_admin_url="http://localhost:8001"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Exception for api errors"""
    pass

class NotFound(Exception):
    """Exception for api errors"""
    pass


class KongAdminApi():

    def __init__(self, url = _default_kong_admin_url):
        self.url = url

    def list_routes(self):
        r=requests.get(self.url+"/routes")
        if r.status_code != 200:
            raise ApiError('Unable to list routes: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()['data']

    def list_certificates(self):
        r=requests.get(self.url+"/certificates")
        if r.status_code != 200:
            raise ApiError('Unable to list certificates: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()['data']

    def update_certificate(self, certificate_id, cert, key, snis=None):
        data={  
                "cert" : cert,
                "key" : key,
                "snis": snis
            }
        data={k: v for k, v in data.items() if v is not None}
        r=requests.patch(self.url+"/certificates/"+certificate_id, json=data)

        if r.status_code != 200:
            raise ApiError('Unable to update certificate: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()
    
    def update_or_create_certificate(self, certificate_id, cert, key, 
            snis=None
            ):
        data={  
                "cert" : cert,
                "key" : key,
                "snis": snis
            }
        data={k: v for k, v in data.items() if v is not None}
        r=requests.put(self.url+"/certificates/"+certificate_id, json=data)

        if r.status_code not in [200, 201]:
            raise ApiError('Unable to update or create certificate: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def add_certificate(self, cert, key, snis):
        data={  
                "cert" : cert,
                "key" : key,
                "snis" : snis
            }
        data={k: v for k, v in data.items() if v is not None}
        r=requests.post(self.url+"/certificates", json=data)

        if r.status_code != 201:
            raise ApiError('Unable to add certificate: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def delete_certificate(self, certificate_id):
        r=requests.delete(self.url+"/certificates/"+certificate_id)

        if r.status_code != 204:
            raise ApiError('Unable to delete certificate: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return
    
    def create_sni(self, sni, certificate_id):
        data={  
                "name":sni,
                "certificate" : {"id":certificate_id}
            }
        data={k: v for k, v in data.items() if v is not None}
        r=requests.post(self.url+"/snis", json=data)

        if r.status_code != 201:
            raise ApiError('Unable to add sni: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def update_sni(self, sni, certificate_id):
        data={  
                "name":sni,
                "certificate" : {"id":certificate_id}
            }
        data={k: v for k, v in data.items() if v is not None}
        r=requests.patch(self.url+"/snis/"+sni, json=data)

        if r.status_code != 200:
            raise ApiError('Unable to update sni: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()

    def delete_sni(self, sni):
        r=requests.delete(self.url+"/snis/"+sni)

        if r.status_code != 204:
            raise ApiError('Unable to delete sni: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return 

    def update_route_protocols(self, route_id, protocols):
        data={  
                "protocols" : protocols
            }
        data={k: v for k, v in data.items() if v is not None}
        r=requests.patch(self.url+"/route/"+route_id, json=data)

        if r.status_code != 200:
            raise ApiError('Unable to update route: '
                'status code: {}, error: {}, request url: {}'
                .format(r.status_code, r.content, r.request.url))
        return r.json()