# YORI Policy: Guest Network Restrictions
# @description Apply stricter limits to guest network devices
# @author YORI Team
# @version 1.0.0

package yori.policies.guest_network

default allow = true
default block = false
default alert = false

# Guest network IP ranges (customize for your network)
guest_ip_ranges = {
    "192.168.10.",   # Guest VLAN
    "10.10.10.",     # IoT/Guest network
}

# Daily request limit for guests
guest_daily_limit = 20

# Check if IP is from guest network
is_guest_ip if {
    some prefix in guest_ip_ranges
    startswith(input.client_ip, prefix)
}

# Block guest devices that exceed limit
block if {
    is_guest_ip
    input.daily_request_count > guest_daily_limit
}

# Alert on guest network usage
alert if {
    is_guest_ip
    not block
}

# Allow trusted network traffic
allow if {
    not block
}
