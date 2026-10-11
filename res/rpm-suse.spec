Name:       ironfloor
Version:    1.1.9
Release:    0
Summary:    RPM package
License:    GPL-3.0
Requires:   gtk3 libxcb1 libXfixes3 alsa-utils libXtst6 libva2 gstreamer-plugins-base gstreamer-plugin-pipewire
Recommends: libayatana-appindicator3-1 xdotool

# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/

%description
The best open-source remote desktop client software, written in Rust.

%prep
# we have no source, so nothing here

%build
# we have no source, so nothing here

%global __python %{__python3}

%install
mkdir -p %{buildroot}/usr/bin/
mkdir -p %{buildroot}/usr/share/ironfloor/
mkdir -p %{buildroot}/usr/share/ironfloor/files/
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps/
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps/
install -m 755 $HBB/target/release/ironfloor %{buildroot}/usr/bin/ironfloor
install $HBB/libsciter-gtk.so %{buildroot}/usr/share/ironfloor/libsciter-gtk.so
install $HBB/res/ironfloor.service %{buildroot}/usr/share/ironfloor/files/
install $HBB/res/128x128@2x.png %{buildroot}/usr/share/icons/hicolor/256x256/apps/ironfloor.png
install $HBB/res/scalable.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/ironfloor.svg
install $HBB/res/ironfloor.desktop %{buildroot}/usr/share/ironfloor/files/
install $HBB/res/ironfloor-link.desktop %{buildroot}/usr/share/ironfloor/files/

%files
/usr/bin/ironfloor
/usr/share/ironfloor/libsciter-gtk.so
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
    rm /usr/share/applications/ironfloor.desktop || true
    rm /usr/share/applications/ironfloor-link.desktop || true
    update-desktop-database
  ;;
  1)
    # for upgrade
  ;;
esac
