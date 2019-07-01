# Certbot-kong
Certbot-kong is a plugin for [Certbot](https://certbot.eff.org/) to install HTTPS certificates for [Kong](https://konghq.com/kong/). Certbot is the tool which is commonly used to automatically obtain, renew and install certificates issued by [Let's Encrypt](https://letsencrypt.org/) or any other CA that uses the ACME protocol.

The plugin uses the Kong admin API to manipulate the route, certificate, SNI and service resources to enable Kong to respond to ACME http-01 challenges, install certificates and configure service routes to use HTTPS.

## Setup certbot-kong
The certbot-kong plugin can be installed using pip.
```sh
pip install ./certbot-kong
```
Python [pip](https://pypi.org/project/pip/) and [setuptools](https://pypi.org/project/setuptools/) will need to be installed on your system.

For Ubuntu 18.04 these can be installed by:
```sh
apt-get update
apt-get -y install python-pip python-setuptools python-wheel
```

## Usage
To obtain and install HTTPS certificates in Kong run:
```sh
KONG_ADMIN_URL=http://localhost:8001
DOMAINS=example.com,abc.example.com,www.example.com
EMAIL=ben@example.com
certbot run --domains $DOMAINS --email $EMAIL \
  -a certbot-kong:kong -i certbot-kong:kong \
  --certbot-kong:kong-admin-url $KONG_ADMIN_URL
```
Set `KONG_ADMIN_URL`, `DOMAINS` and `EMAIL` as required for your environment.

This will configure Kong to respond to http-01 challenges to verify ownership of the domains so that a certificate can be obtained. The issued certificate is then installed in Kong with the following operations:
1. Create certificate object for the issued certificate
2. Create or update SNIs that match the certificates domains (for wildcard certificates, SNIs will also be created from matching route hosts)
3. Delete certifciates which no longer have any SNIs

### Advanced Usage 
Refer to certbot documentation for usage of certbot https://certbot.eff.org/docs/using.html. As certbot-kong is a plugin for certbot the documentation describes other common usage such as automated certificate renewal.

Certbot-kong has both authenticator and installer plugin components which can be substituted with other plugins as requried. See https://certbot.eff.org/docs/using.html#combining-plugins.

For certbot-kong plugin configuration options run:
```sh
certbot --help certbot-kong:kong
```
