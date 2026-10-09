#!/usr/bin/env bash
# One-time setup on the Raspberry Pi 5. Run from this folder:
#   bash install_pi.sh
# After this, the eyes start by themselves every time the Pi gets power.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Setting up wolf eyes from: $DIR"

echo "1/5 Installing pygame (+ unclutter, which hides the cursor on X11 desktops)..."
sudo apt-get update && sudo apt-get install -y python3-pygame unclutter

echo "2/5 Log into the desktop automatically on boot..."
sudo raspi-config nonint do_boot_behaviour B4

echo "3/5 Turning off screen blanking..."
sudo raspi-config nonint do_blanking 1

echo "4/5 Checking sound files..."
ls "$DIR"/sounds/*/* >/dev/null 2>&1 && echo "    $(ls "$DIR"/sounds/*/* | wc -l) sound files found" || echo "    WARNING: no sounds in $DIR/sounds"

echo "5/5 Start the eyes on every boot..."
chmod +x "$DIR/run_wolf.sh" "$DIR/wolf_eyes.py"
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/wolf-eyes.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Big Bad Wolf Eyes
Exec="$DIR/run_wolf.sh"
X-GNOME-Autostart-enabled=true
EOF
echo "    wrote ~/.config/autostart/wolf-eyes.desktop"

echo
echo "Done! Reboot to test:  sudo reboot"
echo "To stop it starting on boot:  rm ~/.config/autostart/wolf-eyes.desktop"
