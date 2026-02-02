# YORI Policy: Admin Device Bypass
# @description Allow admin devices to bypass all restrictions
# @author YORI Team
# @version 1.0.0

package yori.policies.admin_bypass

default allow = false
default block = false
default alert = false

# Admin device IPs (configure for your network)
admin_ips = {
    "192.168.1.10",   # Admin workstation
    "192.168.1.11",   # Admin laptop
}

# Always allow admin devices
allow if {
    input.client_ip == admin_ips[_]
}

# Log admin usage for auditing (alert but don't block)
alert if {
    input.client_ip == admin_ips[_]
}

# Non-admin devices: defer to other policies (allow by default here)
allow if {
    not input.client_ip == admin_ips[_]
}
