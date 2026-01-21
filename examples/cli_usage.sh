#!/bin/bash
#
# YORI CLI Usage Examples
#
# This script demonstrates how to use the YORI CLI to manage allowlist,
# time exceptions, and emergency override.
#

set -e

YORI_CLI="python3 python/yori/cli.py"

echo "========================================="
echo "YORI CLI Usage Examples"
echo "========================================="
echo

# Example 1: Add permanent device
echo "Example 1: Add permanent device to allowlist"
echo "$ $YORI_CLI allowlist add 192.168.1.100 \"Dad's Laptop\" --mac aa:bb:cc:dd:ee:ff --permanent --group family"
echo

# Example 2: Add temporary device (1 hour)
echo "Example 2: Add temporary allowlist (1 hour)"
echo "$ $YORI_CLI allowlist add 192.168.1.200 \"Guest Device\" --expires 1h --notes \"Visitor today\""
echo

# Example 3: List all devices
echo "Example 3: List all allowlisted devices"
echo "$ $YORI_CLI allowlist list"
echo

# Example 4: Check if IP is allowlisted
echo "Example 4: Check if device is allowlisted"
echo "$ $YORI_CLI allowlist check 192.168.1.100"
echo

# Example 5: Remove device
echo "Example 5: Remove device from allowlist"
echo "$ $YORI_CLI allowlist remove 192.168.1.200"
echo

echo "========================================="
echo "Time-Based Exceptions"
echo "========================================="
echo

# Example 6: Add homework hours exception
echo "Example 6: Add homework hours (Mon-Fri 3-6pm)"
echo "$ $YORI_CLI time add homework_hours \\"
echo "    --description \"Allow LLM for homework\" \\"
echo "    --days monday,tuesday,wednesday,thursday,friday \\"
echo "    --start 15:00 --end 18:00 \\"
echo "    --devices 192.168.1.102"
echo

# Example 7: Add weekend exception
echo "Example 7: Add weekend exception"
echo "$ $YORI_CLI time add weekend_access \\"
echo "    --days saturday,sunday \\"
echo "    --start 09:00 --end 21:00 \\"
echo "    --devices 192.168.1.102"
echo

# Example 8: List time exceptions
echo "Example 8: List all time exceptions"
echo "$ $YORI_CLI time list"
echo

# Example 9: Remove time exception
echo "Example 9: Remove time exception"
echo "$ $YORI_CLI time remove homework_hours"
echo

echo "========================================="
echo "Emergency Override"
echo "========================================="
echo

# Example 10: Set emergency password
echo "Example 10: Set emergency override password"
echo "$ $YORI_CLI emergency setpassword \"secure_password_123\""
echo

# Example 11: Check emergency status
echo "Example 11: Check emergency override status"
echo "$ $YORI_CLI emergency status"
echo

# Example 12: Activate emergency override
echo "Example 12: Activate emergency override"
echo "$ $YORI_CLI emergency activate --password \"secure_password_123\" --activated-by admin"
echo

# Example 13: Deactivate emergency override
echo "Example 13: Deactivate emergency override"
echo "$ $YORI_CLI emergency deactivate --password \"secure_password_123\""
echo

echo "========================================="
echo "Common Workflows"
echo "========================================="
echo

echo "Workflow 1: Quick guest access (1 hour)"
echo "---------------------------------------"
echo "$ $YORI_CLI allowlist add 192.168.1.201 \"Guest\" --expires 1h"
echo

echo "Workflow 2: Setup family devices"
echo "---------------------------------------"
echo "$ $YORI_CLI allowlist add 192.168.1.100 \"Dad's Laptop\" --permanent --group family"
echo "$ $YORI_CLI allowlist add 192.168.1.101 \"Mom's iPad\" --permanent --group family"
echo "$ $YORI_CLI allowlist add 192.168.1.102 \"Kid's Laptop\" --group family"
echo

echo "Workflow 3: Homework schedule"
echo "---------------------------------------"
echo "$ $YORI_CLI time add homework \\"
echo "    --days monday,tuesday,wednesday,thursday,friday \\"
echo "    --start 15:00 --end 18:00 \\"
echo "    --devices 192.168.1.102"
echo

echo "Workflow 4: Emergency situation"
echo "---------------------------------------"
echo "$ $YORI_CLI emergency activate --password admin123"
echo "# Do emergency work..."
echo "$ $YORI_CLI emergency deactivate --password admin123"
echo

echo "========================================="
echo "For more help:"
echo "  $YORI_CLI --help"
echo "  $YORI_CLI allowlist --help"
echo "  $YORI_CLI time --help"
echo "  $YORI_CLI emergency --help"
echo "========================================="
