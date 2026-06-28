#!/bin/bash
# setup_zram.sh
# Sets up a compressed RAM disk (zram) equivalent to 50% of physical RAM

echo "Setting up zram..."

# 1. Load kernel module
sudo modprobe zram

# 2. Set compression algorithm to lz4 (fastest)
sudo sh -c 'echo lz4 > /sys/block/zram0/comp_algorithm'

# 3. Calculate 50% of total physical RAM in MB, convert to GB for zram
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
HALF_RAM_GB=$(($TOTAL_RAM_MB / 2048))
if [ "$HALF_RAM_GB" -lt 1 ]; then
    HALF_RAM_GB=1 # Default minimum 1GB
fi

echo "Setting zram size to ${HALF_RAM_GB}G..."
sudo sh -c "echo ${HALF_RAM_GB}G > /sys/block/zram0/disksize"

# 4. Format and activate as swap
sudo mkswap /dev/zram0
sudo swapon /dev/zram0 --priority 100

# 5. Verify
zramctl

echo "Zram setup complete."
