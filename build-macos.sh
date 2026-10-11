#!/usr/bin/env bash
# Build IronFloor.app on Apple Silicon macOS.
# Idempotent: safe to re-run; patches are only applied when missing.
set -euo pipefail

cd "$(dirname "$0")"

APP="./flutter/build/macos/Build/Products/Release/IronFloor.app"
FLUTTER_VERSION_REQUIRED="3.24.5"
VCPKG_COMMIT_ID="9e593bb18ea69cc5095e012465dcd675a822ed0d"

fail() { echo "error: $*" >&2; exit 1; }

# --- prerequisites ---

command -v flutter >/dev/null || fail "flutter not found in PATH (need $FLUTTER_VERSION_REQUIRED)"
command -v rustc >/dev/null || fail "rustc not found in PATH"
command -v pkg-config >/dev/null || fail "pkg-config not found (brew install pkg-config)"
command -v nasm >/dev/null || fail "nasm not found (need NASM 2.x: brew install nasm@2 && brew link --force nasm@2)"
command -v flutter_rust_bridge_codegen >/dev/null || fail "flutter_rust_bridge_codegen not found (see header of this script)"

FLUTTER_ACTUAL="$(flutter --version --machine 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["frameworkVersion"])' 2>/dev/null || flutter --version | awk 'NR==1{print $2}')"
if [ "$FLUTTER_ACTUAL" != "$FLUTTER_VERSION_REQUIRED" ]; then
  fail "flutter $FLUTTER_VERSION_REQUIRED required, found $FLUTTER_ACTUAL"
fi

RUST_MAJOR_MINOR="$(rustc --version | awk '{print $2}' | cut -d. -f1-2)"
if [ "$RUST_MAJOR_MINOR" != "1.81" ]; then
  echo "warning: macOS builds pin Rust 1.81 (workflow MAC_RUST_VERSION); you have $RUST_MAJOR_MINOR" >&2
  read -r -p "continue anyway? [y/N] " ans
  [ "$ans" = "y" ] || fail "aborted"
fi

if [ -z "${VCPKG_ROOT:-}" ] || [ ! -x "$VCPKG_ROOT/vcpkg" ]; then
  fail "VCPKG_ROOT not set or vcpkg missing. Setup:
  git clone https://github.com/microsoft/vcpkg ~/vcpkg
  cd ~/vcpkg && git checkout $VCPKG_COMMIT_ID && ./bootstrap-vcpkg.sh
  export VCPKG_ROOT=\$HOME/vcpkg   # add to ~/.zshrc"
fi

echo "== vcpkg dependencies (skipped if already installed) =="
if [ ! -d "$VCPKG_ROOT/installed/arm64-osx" ]; then
  (cd "$VCPKG_ROOT" && git checkout -q "$VCPKG_COMMIT_ID")
  "$VCPKG_ROOT/vcpkg" install --x-install-root="$VCPKG_ROOT/installed"
else
  echo "already installed"
fi

# --- flutter SDK patches (idempotent) ---

FLUTTER_DIR="$(dirname "$(dirname "$(command -v flutter)")")"
DROPDOWN="$FLUTTER_DIR/packages/flutter/lib/src/material/dropdown_menu.dart"
if [ -f "$DROPDOWN" ] && ! grep -q "enableFilter" "$DROPDOWN"; then
  echo "== patching flutter SDK (dropdown_menu) =="
  git -C "$FLUTTER_DIR" apply .github/patches/flutter_3.24.4_dropdown_menu_enableFilter.diff ||
    echo "warning: dropdown patch did not apply" >&2
fi

BINDING="$FLUTTER_DIR/packages/flutter/lib/src/scheduler/binding.dart"
if grep -q "_setFramesEnabledState(false);" "$BINDING"; then
  echo "== patching flutter SDK (scheduler workaround, flutter/flutter#133533) =="
  sed -i '' 's/_setFramesEnabledState(false);/\/\/_setFramesEnabledState(false);/g' "$BINDING"
fi

# --- deployment target for Apple Silicon (idempotent, matches CI aarch64 job) ---

MIN_MACOS_VERSION="12.3"
sed -i '' "s/MACOSX_DEPLOYMENT_TARGET=[0-9]*.[0-9]*/MACOSX_DEPLOYMENT_TARGET=${MIN_MACOS_VERSION}/" build.py
sed -i '' "s/platform :osx, '.*'/platform :osx, '${MIN_MACOS_VERSION}'/" flutter/macos/Podfile
sed -i '' "s/osx_minimum_system_version = \"[0-9]*.[0-9]*\"/osx_minimum_system_version = \"${MIN_MACOS_VERSION}\"/" Cargo.toml
sed -i '' "s/MACOSX_DEPLOYMENT_TARGET = [0-9]*.[0-9]*;/MACOSX_DEPLOYMENT_TARGET = ${MIN_MACOS_VERSION};/" flutter/macos/Runner.xcodeproj/project.pbxproj

# --- bridge codegen (gitignored files, regenerated every build) ---

echo "== generating flutter rust bridge =="
cp flutter/pubspec.yaml flutter/pubspec.yaml.bak
sed -i '' 's/extended_text: 14.0.0/extended_text: 13.0.0/g' flutter/pubspec.yaml
(cd flutter && flutter pub get)
flutter_rust_bridge_codegen \
  --rust-input ./src/flutter_ffi.rs \
  --dart-output ./flutter/lib/generated_bridge.dart \
  --c-output ./flutter/macos/Runner/bridge_generated.h
cp flutter/macos/Runner/bridge_generated.h flutter/ios/Runner/bridge_generated.h
mv flutter/pubspec.yaml.bak flutter/pubspec.yaml
(cd flutter && flutter pub get)

# --- build ---

echo "== building (cargo + flutter/xcodebuild; first run is slow) =="
./build.py --flutter

echo
echo "== done =="
echo "App: $APP"
echo
echo "Artifact audit (must print nothing):"
cat <<EOF
  find "$APP" -type f \\( -name '*.dylib' -o -perm +111 \\) -exec sh -c \\
    'strings "\$1" | grep -iE "rustdesk|carriez|purslane" && echo "HIT: \$1"' _ {} \\;
EOF
