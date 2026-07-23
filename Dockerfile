FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    wget \
    net-tools \
    iproute2 \
    iptables \
    && rm -rf /var/lib/apt/lists/*

# Copy setup script
COPY setup_openvpn.py /app/setup_openvpn.py

# Make script executable
RUN chmod +x /app/setup_openvpn.py

# Expose port (Render will override this with PORT env variable)
EXPOSE 10000

# Run setup script
CMD ["python3", "/app/setup_openvpn.py"]
