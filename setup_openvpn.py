#!/usr/bin/env python3
"""
OpenVPN Auto-Setup Script for Render
This script installs and configures OpenVPN server on Render platform
"""

import os
import sys
import subprocess
import socket
import hashlib
import random
import string
import time

def run_command(command, shell=False):
    """Execute shell command and return output"""
    try:
        if shell:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command.split(), capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error executing command: {e}")
        return ""

def get_render_domain():
    """Get the Render assigned domain"""
    # Render sets RENDER_EXTERNAL_HOSTNAME environment variable
    domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
    if not domain:
        # Try to get from hostname
        domain = socket.gethostname()
        if not domain or '.' not in domain:
            # Generate a placeholder domain
            domain = f"vpn-{socket.gethostname()}.onrender.com"
    
    # Ensure it's a proper domain
    if '.onrender.com' not in domain:
        domain = f"{domain}.onrender.com"
    
    return domain

def install_openvpn():
    """Install OpenVPN and required packages"""
    print("=" * 50)
    print("Installing OpenVPN and dependencies...")
    print("=" * 50)
    
    # Update package list
    run_command("apt-get update -y", shell=True)
    
    # Install OpenVPN and easy-rsa
    packages = [
        "openvpn",
        "easy-rsa",
        "iptables",
        "openssl",
        "ca-certificates",
        "gnupg",
        "curl"
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        run_command(f"apt-get install -y {package}", shell=True)
    
    print("OpenVPN installation completed!")

def setup_easy_rsa():
    """Setup Easy-RSA for certificate generation"""
    print("\n" + "=" * 50)
    print("Setting up Easy-RSA...")
    print("=" * 50)
    
    # Create easy-rsa directory
    run_command("mkdir -p /etc/openvpn/easy-rsa", shell=True)
    
    # Copy easy-rsa files
    run_command("cp -r /usr/share/easy-rsa/* /etc/openvpn/easy-rsa/", shell=True)
    
    # Change to easy-rsa directory
    os.chdir("/etc/openvpn/easy-rsa")
    
    # Initialize PKI
    run_command("./easyrsa init-pki", shell=True)
    
    # Build CA (non-interactive)
    run_command('echo -e "\\n" | ./easyrsa build-ca nopass', shell=True)
    
    # Generate server certificate
    run_command('echo -e "\\n" | ./easyrsa gen-req server nopass', shell=True)
    run_command('echo -e "yes\\n" | ./easyrsa sign-req server server', shell=True)
    
    # Generate Diffie-Hellman parameters
    print("Generating DH parameters (this may take a while)...")
    run_command("./easyrsa gen-dh", shell=True)
    
    # Generate TA key
    run_command("openvpn --genkey --secret /etc/openvpn/easy-rsa/ta.key", shell=True)
    
    # Copy certificates to OpenVPN directory
    run_command("cp /etc/openvpn/easy-rsa/pki/ca.crt /etc/openvpn/", shell=True)
    run_command("cp /etc/openvpn/easy-rsa/pki/issued/server.crt /etc/openvpn/", shell=True)
    run_command("cp /etc/openvpn/easy-rsa/pki/private/server.key /etc/openvpn/", shell=True)
    run_command("cp /etc/openvpn/easy-rsa/pki/dh.pem /etc/openvpn/", shell=True)
    run_command("cp /etc/openvpn/easy-rsa/ta.key /etc/openvpn/", shell=True)
    
    print("Easy-RSA setup completed!")

def create_server_config(domain):
    """Create OpenVPN server configuration"""
    print("\n" + "=" * 50)
    print("Creating OpenVPN server configuration...")
    print("=" * 50)
    
    # Use Render's port (usually 10000)
    port = os.environ.get('PORT', '10000')
    
    server_config = f"""# OpenVPN Server Configuration for Render
port {port}
proto tcp
dev tun

# Certificates
ca /etc/openvpn/ca.crt
cert /etc/openvpn/server.crt
key /etc/openvpn/server.key
dh /etc/openvpn/dh.pem
tls-auth /etc/openvpn/ta.key 0

# Network settings
server 10.8.0.0 255.255.255.0
topology subnet
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"
keepalive 10 120

# Security
cipher AES-256-GCM
auth SHA256
data-ciphers AES-256-GCM:AES-128-GCM:AES-256-CBC
tls-version-min 1.2
tls-cipher TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384
verify-client-cert none
username-as-common-name

# Performance
max-clients 5
persist-key
persist-tun

# Logging
status /var/log/openvpn-status.log
log /var/log/openvpn.log
verb 3

# Misc
explicit-exit-notify 1
duplicate-cn
"""
    
    with open("/etc/openvpn/server.conf", "w") as f:
        f.write(server_config)
    
    print(f"Server configuration created on port {port}")

def create_client_config(domain):
    """Create a client configuration file"""
    print("\n" + "=" * 50)
    print("Creating client configuration...")
    print("=" * 50)
    
    port = os.environ.get('PORT', '10000')
    
    # Generate client certificate
    os.chdir("/etc/openvpn/easy-rsa")
    client_name = "client1"
    run_command(f'echo -e "\\n" | ./easyrsa gen-req {client_name} nopass', shell=True)
    run_command(f'echo -e "yes\\n" | ./easyrsa sign-req client {client_name}', shell=True)
    
    # Read certificates
    with open("/etc/openvpn/ca.crt", "r") as f:
        ca_cert = f.read()
    
    with open(f"/etc/openvpn/easy-rsa/pki/issued/{client_name}.crt", "r") as f:
        client_cert = f.read()
    
    with open(f"/etc/openvpn/easy-rsa/pki/private/{client_name}.key", "r") as f:
        client_key = f.read()
    
    with open("/etc/openvpn/ta.key", "r") as f:
        ta_key = f.read()
    
    # Create client config
    client_config = f"""client
dev tun
proto tcp
remote {domain} {port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
auth SHA256
data-ciphers AES-256-GCM:AES-128-GCM:AES-256-CBC
verb 3

<ca>
{ca_cert}</ca>
<cert>
{client_cert}</cert>
<key>
{client_key}</key>
<tls-auth>
{ta_key}</tls-auth>
key-direction 1
"""
    
    # Save client config
    config_path = "/etc/openvpn/client.ovpn"
    with open(config_path, "w") as f:
        f.write(client_config)
    
    print(f"Client configuration saved to {config_path}")
    
    # Print the configuration
    print("\n" + "=" * 50)
    print("YOUR OPENVPN CLIENT CONFIGURATION:")
    print("=" * 50)
    print(client_config)
    print("=" * 50)
    
    return client_config

def setup_iptables():
    """Setup iptables rules for NAT"""
    print("\n" + "=" * 50)
    print("Setting up iptables rules...")
    print("=" * 50)
    
    # Enable IP forwarding
    run_command("echo 1 > /proc/sys/net/ipv4/ip_forward", shell=True)
    
    # Add to sysctl for persistence
    run_command("echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf", shell=True)
    
    # Get network interface
    interface = run_command("ip route | grep default | awk '{print $5}'")
    if not interface:
        interface = "eth0"
    
    # Setup iptables rules
    iptables_commands = [
        "iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o " + interface + " -j MASQUERADE",
        "iptables -A FORWARD -s 10.8.0.0/24 -j ACCEPT",
        "iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT"
    ]
    
    for cmd in iptables_commands:
        run_command(cmd, shell=True)
    
    print("Iptables rules configured!")

def start_openvpn():
    """Start OpenVPN server"""
    print("\n" + "=" * 50)
    print("Starting OpenVPN server...")
    print("=" * 50)
    
    # Create log directory
    run_command("mkdir -p /var/log", shell=True)
    
    # Start OpenVPN
    os.system("openvpn --config /etc/openvpn/server.conf --daemon")
    
    time.sleep(3)
    
    # Check if OpenVPN is running
    result = run_command("ps aux | grep openvpn | grep -v grep")
    if result:
        print("OpenVPN server is running!")
    else:
        print("Warning: OpenVPN server might not have started properly")

def save_config_info(domain):
    """Save configuration information to a file"""
    port = os.environ.get('PORT', '10000')
    
    info = f"""
OpenVPN Server Information
==========================
Domain: {domain}
Port: {port}
Protocol: TCP
Config file location: /etc/openvpn/client.ovpn

To connect:
1. Download the client.ovpn file
2. Import it into your OpenVPN client
3. Connect to the VPN

Note: Since Render uses shared resources, the VPN might have limitations.
For production use, consider using a dedicated VPS.
"""
    
    with open("/etc/openvpn/connection_info.txt", "w") as f:
        f.write(info)
    
    print(info)

def main():
    """Main function to run the setup"""
    print("""
╔══════════════════════════════════════════╗
║     OpenVPN Setup for Render Platform    ║
╚══════════════════════════════════════════╝
    """)
    
    try:
        # Get domain from Render
        domain = get_render_domain()
        print(f"Detected Render domain: {domain}")
        
        # Check if running as root
        if os.geteuid() != 0:
            print("This script must be run as root!")
            sys.exit(1)
        
        # Run setup steps
        install_openvpn()
        setup_easy_rsa()
        create_server_config(domain)
        setup_iptables()
        start_openvpn()
        
        # Create and display client config
        client_config = create_client_config(domain)
        save_config_info(domain)
        
        print("\n" + "=" * 50)
        print("✅ OpenVPN setup completed successfully!")
        print("=" * 50)
        print(f"\nConnect to your VPN server at: {domain}")
        print("Download the client.ovpn file to connect!")
        
        # Keep the script running for Render
        print("\nKeeping server alive...")
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during setup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
