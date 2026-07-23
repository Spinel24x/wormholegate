#!/bin/bash

echo "🚀 Starting OpenVPN Server on Fly.io..."

# چک کردن وجود کانفیگ
if [ ! -f /etc/openvpn/server.conf ]; then
    echo "⚙️ First run - Setting up OpenVPN..."
    /app/setup.sh
else
    echo "✅ Config exists, starting OpenVPN..."
fi

# فعال‌سازی IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# استارت OpenVPN
echo "🎯 Starting OpenVPN..."
openvpn --config /etc/openvpn/server.conf --daemon

# صبر برای استارت
sleep 3

# چک کردن
if pgrep -x "openvpn" > /dev/null; then
    echo "✅ OpenVPN is running!"
else
    echo "❌ OpenVPN failed to start!"
    openvpn --config /etc/openvpn/server.conf &
fi

# نمایش IP
echo ""
echo "📡 Server Public IP: $(curl -s ifconfig.me)"
echo "🔌 OpenVPN Port: 443 (TCP)"
echo ""

# نمایش کانفیگ کلاینت (برای کپی کردن)
if [ -f /etc/openvpn/clients/client1.ovpn ]; then
    echo "📋 Copy this config to your client:"
    echo "================================"
    cat /etc/openvpn/clients/client1.ovpn
    echo "================================"
fi

# Keep container alive
echo "✅ Server is ready!"
while true; do
    sleep 60
    # چک هندلث برای Fly.io
    if ! pgrep -x "openvpn" > /dev/null; then
        echo "⚠️ OpenVPN died, restarting..."
        openvpn --config /etc/openvpn/server.conf --daemon
    fi
done
