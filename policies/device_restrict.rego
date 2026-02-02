# YORI Policy: Device Restrictions
# @description Allow/deny specific devices by IP address
# @author YORI Team
# @version 1.0.0

package yori.policies.device_restrict

default allow = true
default block = false

# Blocked devices (add IPs to block)
blocked_devices = {
    # "192.168.1.100",  # Example: Kids tablet
    # "192.168.1.101",  # Example: Guest device
}

# Block requests from blocked devices
block if {
    input.client_ip in blocked_devices
}

# Allowed devices bypass all other policies
allowed_devices = {
    # "192.168.1.1",    # Example: Admin workstation
}

allow if {
    input.client_ip in allowed_devices
}
