#!/bin/bash

echo "🔧 Starting OpenVPN Setup on Fly.io..."

# گرفتن IP عمومی از Fly.io
PUBLIC_IP=$(curl -s ifconfig.me)
echo "Public IP: $PUBLIC_IP"

# تنظیمات Easy-RSA
echo "📜 Generating Certificates..."
cd /etc/openvpn

# کپی easy-rsa
cp -r /usr/share/easy-rsa /etc/openvpn/
cd /etc/openvpn/easy-rsa

# ساخت PKI
./easyrsa init-pki
echo -e "\n" | ./easyrsa build-ca nopass
echo -e "\n" | ./easyrsa gen-req server nopass
echo -e "yes\n" | ./easyrsa sign-req server server

# ساخت DH
echo "🔑 Generating DH parameters..."
./easyrsa gen-dh

# ساخت TA key
openvpn --genkey --secret /etc/openvpn/easy-rsa/ta.key

# کپی فایل‌ها
cp pki/ca.crt /etc/openvpn/
cp pki/issued/server.crt /etc/openvpn/
cp pki/private/server.key /etc/openvpn/
cp pki/dh.pem /etc/openvpn/
cp ta.key /etc/openvpn/

# ساخت کانفیگ سرور
echo "⚙️ Creating Server Config..."
cat > /etc/openvpn/server.conf << EOF
# OpenVPN Server Config for Fly.io
port 443
proto tcp
dev tun

# Certificates
ca /etc/openvpn/ca.crt
cert /etc/openvpn/server.crt
key /etc/openvpn/server.key
dh /etc/openvpn/dh.pem
tls-auth /etc/openvpn/ta.key 0

# Network
server 10.8.0.0 255.255.255.0
topology subnet
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 1.1.1.1"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"

# Security
cipher AES-256-GCM
auth SHA256
data-ciphers AES-256-GCM:AES-128-GCM
data-ciphers-fallback AES-256-CBC
tls-version-min 1.2
tls-cipher TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384

# Performance
keepalive 10 120
max-clients 5
persist-key
persist-tun

# Logs
status /var/log/openvpn-status.log
log /var/log/openvpn.log
verb 3

# Misc
explicit-exit-notify 1
duplicate-cn
EOF

echo "✅ Server Config Created"

# ساخت کانفیگ کلاینت
echo "👤 Creating Client Config..."
cd /etc/openvpn/easy-rsa

# ساخت کلاینت
echo -e "\n" | ./easyrsa gen-req client1 nopass
echo -e "yes\n" | ./easyrsa sign-req client client1

# ساخت فایل ovpn
cat > /etc/openvpn/clients/client1.ovpn << EOF
client
dev tun
proto tcp
remote ${PUBLIC_IP} 443
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
auth SHA256
data-ciphers AES-256-GCM:AES-128-GCM
verb 3
key-direction 1

<ca>
$(cat /etc/openvpn/ca.crt)
</ca>
<cert>
$(cat /etc/openvpn/easy-rsa/pki/issued/client1.crt)
</cert>
<key>
$(cat /etc/openvpn/easy-rsa/pki/private/client1.key)
</key>
<tls-auth>
$(cat /etc/openvpn/ta.key)
</tls-auth>
EOF

echo "✅ Client Config Created at /etc/openvpn/clients/client1.ovpn"

# تنظیم iptables
echo "🔥 Setting up Firewall..."
echo 1 > /proc/sys/net/ipv4/ip_forward

# پیدا کردن اینترفیس
INTERFACE=$(ip route | grep default | awk '{print $5}')
echo "Network Interface: $INTERFACE"

iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o $INTERFACE -j MASQUERADE
iptables -A FORWARD -s 10.8.0.0/24 -j ACCEPT
iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT

echo "✅ Setup Complete!"
echo ""
echo "📋 Client Config:"
echo "================================"
cat /etc/openvpn/clients/client1.ovpn
echo "================================"
