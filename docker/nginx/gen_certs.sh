#!/bin/bash
set -e
mkdir -p docker/nginx/certs
pushd docker/nginx/certs >/dev/null

# CA key and cert
openssl genrsa -out ca.key.pem 4096
openssl req -x509 -new -nodes -key ca.key.pem -sha256 -days 1825 -out ca.crt.pem -subj "//CN=local-ca"

# Server key and CSR
openssl genrsa -out server.key.pem 4096
openssl req -new -key server.key.pem -out server.csr.pem -subj "//CN=localhost"

# Sign server cert with CA
openssl x509 -req -in server.csr.pem -CA ca.crt.pem -CAkey ca.key.pem -CAcreateserial -out server.crt.pem -days 825 -sha256

# Client key and cert
openssl genrsa -out client.key.pem 4096
openssl req -new -key client.key.pem -out client.csr.pem -subj "//CN=demo-client"
openssl x509 -req -in client.csr.pem -CA ca.crt.pem -CAkey ca.key.pem -CAcreateserial -out client.crt.pem -days 825 -sha256

# For nginx we need cert and key names server.crt, server.key, ca.crt
cp server.crt.pem server.crt
cp server.key.pem server.key
cp ca.crt.pem ca.crt

chmod 644 server.crt server.key ca.crt client.crt client.key
popd >/dev/null

echo "Created certs in docker/nginx/certs. Use client.crt & client.key for demo requests."
