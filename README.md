# Certbot-kong

Certbot-kong is a plugin for [Certbot](https://certbot.eff.org/) to install HTTPS certificates for [Kong](https://konghq.com/kong/). Certbot is the tool which is commonly used to automatically obtain, renew and install certificates issued by [Let's Encrypt](https://letsencrypt.org/) or any other CA that uses the ACME protocol.

The plugin uses the Kong admin API to manipulate the route, certificate, SNI and service resources to enable Kong to respond to ACME http-01 challenges, install certificates and configure service routes to use HTTPS.

## Install certbot-kong

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

## Example Certificate Installation and Renewal

In this example will start with a Kong service and route proxying the github API exposed over http and then use certbot-kong to obtain a certificate and convert the service to be exposed over only https using the new certificate.

## 1. Prerequisites

1. Kong is installed and admin URL can be accessed, see (https://konghq.com/install/)
2. Certbot is installed, see (https://certbot.eff.org/instructions)
3. Certbot-kong is installed as per above

### 2. Setup Environment

Initialise environment variables

```sh
DOMAIN=example.com
KONG_ADMIN_URL=http://localhost:8001
EMAIL=ben@example.com
```

### 3. Create Github API Proxy

Create the Github service and route. The route is created with only the http protocol. Later we will see this converted to https.

```sh
# create the service
curl --data "name=github" --data "url=https://api.github.com" $KONG_ADMIN_URL/services

# create the route
curl --data "protocols[]=http" --data "hosts[]=$DOMAIN" --data "paths[]=/github" $KONG_ADMIN_URL/services/github/routes
```

Note that the service can be accessed over http.

```sh
curl http://$DOMAIN/github/users/bsorahan/repos
```

### 4. Run certbot-kong

Run certbot-kong to obtain and install certificates for routes matching the certificate domains. The `--redirect` flag is also included to enable only https on the matching routes.

```sh
certbot run --domains $DOMAIN --email $EMAIL \
  -a certbot-kong:kong -i certbot-kong:kong \
  --redirect \
  --certbot-kong:kong-admin-url $KONG_ADMIN_URL
```

Note in the output that certbot-kong has added a new certificate, created a SNI which uses the new certificate and updated the github route to enable only the https protocol.

```
...
Adding certificate 9a7e3de3-b6dd-4deb-bc57-7a82846c98f3
Creating SNI example.com with certificate 9a7e3de3-b6dd-4deb-bc57-7a82846c98f3
Updating Route c63a6fa9-c315-4b11-bdab-973ab86f11e7 protocols from ['http'] to ['https']
...
```

Kong Certificate, SNI, Route resources

Now when we try to access the service over http we receive the following error.

The service is now only available over https and is using the new certificate.

### 5. Test automatic renewal

We can verify that the certificate can also be automatically renewed.

```sh
certbot renew --dry-run
```

Depending on your system, steps to setup up automatic certificate renewal may differ. Refer to [certbot](https://certbot.eff.org/instructions) documentation for instruction applicable to your system.
