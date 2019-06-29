# Certbot-kong
Certbot-kong is a plugin for [Certbot](https://certbot.eff.org/) to install HTTPS certificates for [Kong](https://konghq.com/kong/). Certbot is the tool which is commonly used to automatically install and renew [Let's Encrypt](https://letsencrypt.org/) issued certificates.

The plugin uses the Kong admin API to manipulate the route, certificate, SNI and service resources to configure Kong's services to use HTTPS.

Certbot-kong currently has an installer plugin which is capable of installing certificates to Kong that are already managed by certbot (including wildcard certificates). 

The authenticator plugin is not yet implemented.

## Setup certbot-kong
The certbot-kong plugin can be installed using pip.
```
pip install ./certbot-kong
```
Python [pip](https://pypi.org/project/pip/) and [setuptools](https://pypi.org/project/setuptools/) will need to be installed on your system.

For Ubuntu 18.04 these can be installed by:
```
apt-get update
apt-get -y install python-pip python-setuptools python-wheel
```

## Run certbot-kong installer plugin
To install certificates managed in certbot to Kong:
```
KONG_ADMIN_URL=http://localhost:8001
certbot install -i certbot-kong:kong --certbot-kong:kong-admin-url $KONG_ADMIN_URL
```
Set KONG_ADMIN_URL as required for your environment.

On confirmation of the certificate to install the certbot-kong installer plugin will:
1. Create certificate object for the certificate to be installed
2. Create or update SNIs that match the certificates domains (for wildcard certificates, SNIs will also be created from matching route hosts)
3. Delete certifciates which no longer have any SNIs

*Note: To use the installer there needs to be certificates already managed by certbot. These can be obtained as per https://certbot.eff.org/docs/using.html#getting-certificates-and-choosing-plugins.*