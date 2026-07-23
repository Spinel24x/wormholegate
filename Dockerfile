FROM ubuntu:22.04

# نصب پیش‌نیازها
RUN apt-get update && apt-get install -y \
    openvpn \
    easy-rsa \
    iptables \
    curl \
    wget \
    net-tools \
    iproute2 \
    procps \
    nano \
    ufw \
    && rm -rf /var/lib/apt/lists/*

# ساخت دایرکتوری‌های مورد نیاز
RUN mkdir -p /etc/openvpn/easy-rsa
RUN mkdir -p /etc/openvpn/clients
RUN mkdir -p /app

# کپی فایل‌های تنظیمات
COPY start.sh /app/start.sh
COPY setup.sh /app/setup.sh

RUN chmod +x /app/*.sh

# پورت‌های OpenVPN (TCP و UDP)
# Fly.io فقط از این پورت‌ها پشتیبانی می‌کنه
EXPOSE 443/tcp
EXPOSE 443/udp
EXPOSE 80/tcp
EXPOSE 8080/tcp

WORKDIR /app

# استارت اسکریپت
CMD ["/app/start.sh"]
