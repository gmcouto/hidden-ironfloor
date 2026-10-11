Name:       ironfloor
Version:    1.5.0
Release:    0
Summary:    RPM package
License:    GPL-3.0
URL:        https://couto.info
Vendor:     IronFloor <info@couto.info>
Requires:   gtk3 libxcb1 libXfixes3 alsa-utils libXtst6 libva2 gstreamer-plugins-base gstreamer-plugin-pipewire
Recommends: libayatana-appindicator3-1 xdotool
Provides:   libdesktop_drop_plugin.so()(64bit), libdesktop_multi_window_plugin.so()(64bit), libfile_selector_linux_plugin.so()(64bit), libflutter_custom_cursor_plugin.so()(64bit), libflutter_linux_gtk.so()(64bit), libscreen_retriever_plugin.so()(64bit), libtray_manager_plugin.so()(64bit), liburl_launcher_linux_plugin.so()(64bit), libwindow_manager_plugin.so()(64bit), libwindow_size_plugin.so()(64bit), libtexture_rgba_renderer_plugin.so()(64bit)

# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/

%description
The best open-source remote desktop client software, written in Rust.

%prep
# we have no source, so nothing here

%build
# we have no source, so nothing here

# %global __python %{__python3}

%install

mkdir -p "%{buildroot}/usr/share/ironfloor" && cp -r ${HBB}/flutter/build/linux/x64/release/bundle/* -t "%{buildroot}/usr/share/ironfloor"
mkdir -p "%{buildroot}/usr/bin"
install -Dm 644 $HBB/res/ironfloor.service -t "%{buildroot}/usr/share/ironfloor/files"
install -Dm 644 $HBB/res/ironfloor.desktop -t "%{buildroot}/usr/share/ironfloor/files"
install -Dm 644 $HBB/res/ironfloor-link.desktop -t "%{buildroot}/usr/share/ironfloor/files"
install -Dm 644 $HBB/res/128x128@2x.png "%{buildroot}/usr/share/icons/hicolor/256x256/apps/ironfloor.png"
install -Dm 644 $HBB/res/scalable.svg "%{buildroot}/usr/share/icons/hicolor/scalable/apps/ironfloor.svg"

%files
/usr/share/ironfloor/*
/usr/share/ironfloor/files/ironfloor.service
/usr/share/icons/hicolor/256x256/apps/ironfloor.png
/usr/share/icons/hicolor/scalable/apps/ironfloor.svg
/usr/share/ironfloor/files/ironfloor.desktop
/usr/share/ironfloor/files/ironfloor-link.desktop

%changelog
# let's skip this for now

%pre
# can do something for centos7
case "$1" in
  1)
    # for install
  ;;
  2)
    # for upgrade
    systemctl stop ironfloor || true
  ;;
esac

%post
cp /usr/share/ironfloor/files/ironfloor.service /etc/systemd/system/ironfloor.service
cp /usr/share/ironfloor/files/ironfloor.desktop /usr/share/applications/
cp /usr/share/ironfloor/files/ironfloor-link.desktop /usr/share/applications/
ln -sf /usr/share/ironfloor/ironfloor /usr/bin/ironfloor
systemctl daemon-reload
systemctl enable ironfloor
systemctl start ironfloor
update-desktop-database

%preun
case "$1" in
  0)
    # for uninstall
    systemctl stop ironfloor || true
    systemctl disable ironfloor || true
    rm /etc/systemd/system/ironfloor.service || true
  ;;
  1)
    # for upgrade
  ;;
esac

%postun
case "$1" in
  0)
    # for uninstall
    rm /usr/bin/ironfloor || true
    rmdir /usr/lib/ironfloor || true
    rmdir /usr/local/ironfloor || true
    rmdir /usr/share/ironfloor || true
    rm /usr/share/applications/ironfloor.desktop || true
    rm /usr/share/applications/ironfloor-link.desktop || true
    update-desktop-database
  ;;
  1)
    # for upgrade
    rmdir /usr/lib/ironfloor || true
    rmdir /usr/local/ironfloor || true
  ;;
esac
