# Certbot-kong

Certbot-kong is a plugin for [Certbot](https://certbot.eff.org/) to install HTTPS certificates for [Kong](https://konghq.com/kong/). Certbot is the tool which is commonly used to automatically obtain, renew and install certificates issued by [Let's Encrypt](https://letsencrypt.org/) or any other CA that uses the ACME protocol.

The plugin uses the Kong admin API to manipulate the route, certificate, SNI and service resources to enable Kong to respond to ACME http-01 challenges, install certificates and configure service routes to use HTTPS.

## Install certbot-kong

Ensure that your system has access to the Kong admin URL and has [certbot](https://certbot.eff.org/instructions) installed.

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
3. Delete certificates which no longer have any SNIs

### Advanced Usage

Refer to certbot documentation for usage of certbot https://certbot.eff.org/docs/using.html. As certbot-kong is a plugin for certbot the documentation describes other common usage such as automated certificate renewal.

Certbot-kong has both authenticator and installer plugin components which can be substituted with other plugins as required. See https://certbot.eff.org/docs/using.html#combining-plugins.

For certbot-kong plugin configuration options run:

```sh
certbot --help certbot-kong:kong
```

## Example Certificate Installation and Renewal

In this example we will start with a Kong service and route exposed over http and then use certbot-kong to obtain a Let's Encrypt certificate and convert the service to allow only https using the new certificate.

## 1. Prerequisites

1. Kong is installed and admin URL can be accessed, see https://konghq.com/install/
2. Certbot is installed, see https://certbot.eff.org/instructions
3. Certbot-kong is installed as per above

### 2. Setup Environment

Initialise environment variables

```sh
DOMAIN=example.com
KONG_ADMIN_URL=http://localhost:8001
EMAIL=ben@example.com
```

### 3. Create Service and Route

Create the service and route in Kong. The route is created with only the http protocol. Later we will see this converted to https.

For this example we will proxy the Github API with Kong.

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
Adding certificate 723b1e4e-a3ff-457b-ba07-af09cf60852b
Creating SNI example.com with certificate 723b1e4e-a3ff-457b-ba07-af09cf60852b
Updating Route a432a926-f3e7-4492-ba94-ac1e77f8bac3 protocols from ['http'] to ['https']
...
```

We can see this in more detail be looking at the Kong Certificate, SNI and Route resources.

#### Certificate

```sh
curl $KONG_ADMIN_URL/certificates/723b1e4e-a3ff-457b-ba07-af09cf60852b
```

_output_

```json
{
  "created_at": 1581078926,
  "cert": "-----BEGIN CERTIFICATE-----...",
  "id": "723b1e4e-a3ff-457b-ba07-af09cf60852b",
  "tags": null,
  "key": "-----BEGIN PRIVATE KEY-----...",
  "snis": ["example.com"]
}
```

#### SNI

```sh
curl $KONG_ADMIN_URL/snis/example.com
```

_output_

```json
{
  "created_at": 1581078926,
  "id": "f7c5e7f3-01e7-4a5a-abb9-dafe2f0deac2",
  "tags": null,
  "name": "example.com",
  "certificate": { "id": "723b1e4e-a3ff-457b-ba07-af09cf60852b" }
}
```

Note that the SNI is using the certificate.

#### Route

```sh
curl $KONG_ADMIN_URL/routes/a432a926-f3e7-4492-ba94-ac1e77f8bac3
```

_output_

```json
{
  "id": "a432a926-f3e7-4492-ba94-ac1e77f8bac3",
  "path_handling": "v0",
  "paths": ["/github"],
  "destinations": null,
  "headers": null,
  "protocols": ["https"],
  "methods": null,
  "snis": null,
  "service": { "id": "e9755238-85b2-47c3-9831-859d72735584" },
  "name": null,
  "strip_path": true,
  "preserve_host": false,
  "regex_priority": 0,
  "updated_at": 1581078926,
  "sources": null,
  "hosts": ["example.com"],
  "https_redirect_status_code": 426,
  "tags": null,
  "created_at": 1581078795
}
```

Note that https is the only protocol available.

Now when we try to access the service over http we receive the following error.

```sh
curl http://$DOMAIN/github/users/bsorahan/repos
```

_output_

```json
{ "message": "Please use HTTPS protocol" }
```

The service is now only available over https so we can get a successful response using the following.

```sh
curl https://$DOMAIN/github/users/bsorahan/repos
```

We can also see that we are using the certificate issued by Let's Encrypt.

```sh
echo '' | openssl s_client -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -issuer
```

_output_

```
issuer=C = US, O = Let's Encrypt, CN = Let's Encrypt Authority X3
```

### 5. Automatic Certificate Renewal

We can verify that the certificate can also be renewed.

```sh
certbot renew --dry-run
```

Automatic certificate renewal may already have been configured when certbot was installed on your system (i.e. using cron or similar). Refer to [certbot documentation](https://certbot.eff.org/instructions) for instruction applicable to your system.
