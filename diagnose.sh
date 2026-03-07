#!/usr/bin/env bash
echo "=== Session ==="
echo "XDG_SESSION_TYPE: $XDG_SESSION_TYPE"
echo "XDG_CURRENT_DESKTOP: $XDG_CURRENT_DESKTOP"
echo "QT_QPA_PLATFORM: $QT_QPA_PLATFORM"
echo "WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
echo "DISPLAY: $DISPLAY"

echo ""
echo "=== Tools ==="
for t in gdbus grim scrot spectacle gnome-screenshot xwd; do
  which $t 2>/dev/null && echo "✅ $t: $(which $t)" || echo "❌ $t: not found"
done

echo ""
echo "=== D-Bus GNOME Shell ==="
gdbus introspect --session --dest org.gnome.Shell \
  --object-path /org/gnome/Shell 2>&1 | grep -i screenshot || echo "no screenshot iface found"

echo ""
echo "=== D-Bus Screenshot service ==="
gdbus introspect --session --dest org.gnome.Shell.Screenshot \
  --object-path /org/gnome/Shell/Screenshot 2>&1 | head -20

echo ""
echo "=== XDG Portal ==="
gdbus introspect --session --dest org.freedesktop.portal.Desktop \
  --object-path /org/freedesktop/portal/desktop 2>&1 | grep -i screenshot || echo "no portal screenshot"