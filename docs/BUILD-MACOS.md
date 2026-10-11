# Building IronFloor.app on a fresh macOS machine (Apple Silicon)

Target: a single unsigned `IronFloor.app` on arm64 macOS. Everything here mirrors what
`.github/workflows/flutter-build.yml` does in CI (macOS job) plus the bridge generation
from `bridge.yml`, folded into one local flow.

Shortcut: most of this is automated by `./build-macos.sh` (repo root). The manual
background below explains what it does and what to do when it fails.

## 0. Machine assumptions

- Apple Silicon Mac (arm64), macOS 12.3+ (the build pins `MACOSX_DEPLOYMENT_TARGET=12.3`)
- Admin access (some steps install into `/usr/local/bin`)
- ~1 hour wall clock for the first build (mostly vcpkg + Rust LTO), ~10 GB free disk
  (Xcode + vcpkg ffmpeg artifacts + target/)

## 1. One-time toolchain setup

### Xcode (required — the Rust `cc` crate and xcodebuild both need it)

```bash
xcode-select --install          # CLI tools only may work, but full Xcode is safer
sudo xcode-select -s /Applications/Xcode.app  # if multiple toolchains conflict
```

- Open Xcode once and accept the license; install any requested components.
- If `xcodebuild -version` errors about a license, run `sudo xcodebuild -license accept`.

### Homebrew packages

```bash
brew install pkg-config create-dmg llvm
```

`create-dmg` is only needed for DMG packaging (optional for a bare .app).
`llvm` is only needed if Homebrew's clang fights Xcode's; try without it first.

### NASM 2.x — the classic trap

```bash
brew install nasm@2
brew link --force nasm@2
nasm --version   # MUST print 2.x, not 3.x
```

`brew install nasm` (without @2) gets NASM 3.x, which is a rewrite with incompatible
CLI options. `aom`/ffmpeg assembly in vcpkg **fails with confusing errors** on NASM 3.
This is exactly why CI downloads NASM 2.16.03 manually.

### Rust 1.81

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup toolchain install 1.81
rustup default 1.81
rustc --version   # rustc 1.81.x
```

Why not latest stable: the macOS build pulls `cidre` (Apple API bindings) which
requires 1.81; CI pins `MAC_RUST_VERSION: "1.81"`. Other versions may work but are
untested for this tree.

### Flutter 3.24.5 stable

```bash
# via https://docs.flutter.dev/get-started/install/macos, or:
brew install --cask flutter     # if it gives 3.24.5; otherwise download the zip
flutter --version               # must say 3.24.5
```

If you have a different version, the Flutter SDK patches (step 3) and the generated
bridge may not line up — use exactly 3.24.5.

### vcpkg at the pinned commit

```bash
git clone https://github.com/microsoft/vcpkg ~/vcpkg
cd ~/vcpkg
git checkout 9e593bb18ea69cc5095e012465dcd675a822ed0d   # matches vcpkg.json baseline in CI
./bootstrap-vcpkg.sh
echo 'export VCPKG_ROOT=$HOME/vcpkg' >> ~/.zshrc
export VCPKG_ROOT=$HOME/vcpkg
```

Then, from the repo root:

```bash
$VCPKG_ROOT/vcpkg install --x-install-root="$VCPKG_ROOT/installed"
```

This builds ffmpeg, libyuv, etc. for `arm64-osx` — 30–60 min, one time. CI sets
`VCPKG_BINARY_SOURCES: "clear;x-gha,readwrite"` (GitHub cache); locally there is no
cache, so the first build pays full compile cost.

### flutter_rust_bridge codegen

```bash
cargo install cargo-expand --version 1.0.95 --locked
cargo install flutter_rust_bridge_codegen --version 1.80.1 --features uuid --locked
```

## 2. Get the source

```bash
git clone <your-fork-url> ironfloor && cd ironfloor
git checkout ironfloor
```

No submodule init is needed on this branch — `libs/hbb_common` is vendored as plain
files (it was a submodule upstream; on `master` you'd need `git submodule update --init`).

## 3. Flutter SDK patches (two, both required)

CI applies these to the Flutter SDK itself, not the repo:

1. **dropdown_menu patch** — `.github/patches/flutter_3.24.4_dropdown_menu_enableFilter.diff`
2. **scheduler workaround** for flutter/flutter#133533 — comments out
   `_setFramesEnabledState(false);` in the SDK's `scheduler/binding.dart`.

`./build-macos.sh` applies both idempotently. Manually:

```bash
FLUTTER_DIR=$(dirname $(dirname $(which flutter)))
git -C "$FLUTTER_DIR" apply <repo>/.github/patches/flutter_3.24.4_dropdown_menu_enableFilter.diff
sed -i '' 's/_setFramesEnabledState(false);/\/\/_setFramesEnabledState(false);/g' \
  "$FLUTTER_DIR/packages/flutter/lib/src/scheduler/binding.dart"
```

Note: SDK patches live in the Flutter install, not the repo. If you later switch
Flutter versions or reinstall the SDK, re-apply them.

## 4. Generate the bridge files

These are **gitignored** and must be regenerated on every machine (CI does it every
build):

```bash
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
```

The `extended_text` 14→13 downgrade exists because bridge generation resolves deps
with an older Dart SDK constraint; pubspec is restored after. Files produced:
`src/bridge_generated.rs`, `src/bridge_generated.io.rs`,
`flutter/lib/generated_bridge.dart`, `flutter/lib/generated_bridge.freezed.dart`,
`flutter/macos/Runner/bridge_generated.h`.

## 5. Deployment target (Apple Silicon)

CI bumps the minimum macOS version to 12.3 for aarch64. `./build-macos.sh` does these
four seds; manual form:

```bash
sed -i '' 's/MACOSX_DEPLOYMENT_TARGET=[0-9]*.[0-9]*/MACOSX_DEPLOYMENT_TARGET=12.3/' build.py
sed -i '' "s/platform :osx, '.*'/platform :osx, '12.3'/" flutter/macos/Podfile
sed -i '' 's/osx_minimum_system_version = "[0-9]*.[0-9]*"/osx_minimum_system_version = "12.3"/' Cargo.toml
sed -i '' 's/MACOSX_DEPLOYMENT_TARGET = [0-9]*.[0-9]*;/MACOSX_DEPLOYMENT_TARGET = 12.3;/' \
  flutter/macos/Runner.xcodeproj/project.pbxproj
```

These mutate **tracked files** — do not commit them; `git checkout .` reverts.

## 6. Build

```bash
./build.py --flutter
```

or simply `./build-macos.sh` (does steps 3–6, skipping anything already done).

Cargo features CI adds for the macOS release job (`--hwcodec --unix-file-copy-paste
--screencapturekit`): `--hwcodec` needs vcpkg ffmpeg (already built in step 1);
`--screencapturekit` enables the ScreenCaptureKit capture path, recommended on
macOS 12.3+. Add them if you want feature parity with CI artifacts:

```bash
./build.py --flutter --hwcodec --unix-file-copy-paste --screencapturekit
```

**Output:** `flutter/build/macos/Build/Products/Release/IronFloor.app`

Copy to `/Applications` and launch. It is unsigned — first launch needs right-click →
Open (or `xattr -cr` the app) to pass Gatekeeper.

## 7. Optional: DMG + signing + notarization

```bash
# unsigned dmg
create-dmg --icon "IronFloor.app" 200 190 --hide-extension "IronFloor.app" \
  --window-size 800 400 --app-drop-link 600 185 ironfloor-1.5.0.dmg \
  ./flutter/build/macos/Build/Products/Release/IronFloor.app

# signed + notarized (requires Apple Developer Program)
export MACOS_CODESIGN_IDENTITY="Developer ID Application: <your name> (TEAMID)"
./res/osx-dist.sh
# res/osx-dist.sh uses rcodesign (brew install apple-codesign) and expects the
# notarization API key at ~/.p12/api-key.json
```

Without signing, the app works locally and via right-click → Open, but you cannot
silently deploy it to managed fleets, and macOS TCC permission prompts will attribute
the app to "IronFloor" with no signing identity.

## 8. Verify the rebrand (post-build gate)

```bash
APP=./flutter/build/macos/Build/Products/Release/IronFloor.app
# must print nothing:
find "$APP" -type f \( -name '*.dylib' -o -perm +111 \) -exec sh -c \
  'strings "$1" | grep -iE "rustdesk|carriez|purslane" && echo "HIT: $1"' _ {} \;
# must print nothing:
nm -gU "$APP/Contents/MacOS/libironfloor.dylib" | grep -i rustdesk
# must show IronFloor / info.couto.ironfloor / ironfloor scheme:
plutil -p "$APP/Contents/Info.plist"
```

Also smoke test: launch → TCC prompts say "IronFloor"; `open ironfloor://<id>` opens
the app; after granting permissions, the LaunchDaemon/Agent land under
`/Library/LaunchDaemons/info.couto.IronFloor_service.plist` (Label matching filename).

## Known gaps and challenges

1. **AppIcon is still the old artwork** — `flutter/macos/Runner/AppIcon.icns` is a
   binary asset that was not rebranded (needs new artwork). The app name/strings are
   rebranded; the icon is not.
2. **No code-signing identity** — unsigned builds hit Gatekeeper prompts and cannot
   be notarized. For B2B distribution you want a Developer ID Application cert;
   TCC-related permissions (screen recording, accessibility) behave better signed.
3. **Server placeholders are unset by design** — `RS_PUB_KEY` is empty
   (`libs/hbb_common/src/config.rs`), default rendezvous server is `rs.couto.info`,
   version check hits `api.couto.info`. Until you host your own hbbs/hbbr at those
   names (or edit the constants), the client has no default server: enter your
   server in Settings → ID/Relay manually per client.
4. **Updater pin is a placeholder** — `src/updater.rs` only accepts release assets
   from `github.com/couto-info/ironfloor`. Until that repo exists with releases,
   the in-app updater finds nothing (harmless; manual updates only).
5. **First vcpkg build is fragile** — ffmpeg + libyuv compilation is 30–60 min and
   the most common failure point. If it fails: confirm NASM 2.x, confirm
   `VCPKG_ROOT`, and re-run; vcpkg resumes. On Apple Silicon there is no binary
   cache locally (CI uses GitHub-hosted cache).
6. **Flutter version drift** — everything here assumes exactly 3.24.5. A newer
   Flutter breaks the SDK patches and possibly the generated bridge. If you must
   bump Flutter, regenerate the bridge and re-check both SDK patches still apply.
7. **Xcode/Swift version drift** — the Runner is built by whatever Xcode you have.
   Swift 5.x toolchains are fine; very new Xcodes occasionally change how
   `customModule` resolution or bridging headers behave — if the XIB fails to load
   classes at runtime, check `PRODUCT_NAME` in
   `flutter/macos/Runner/Configs/AppInfo.xcconfig` is still `IronFloor` (the Swift
   module name derives from it).
8. **Rosetta not needed** — the build is single-arch arm64 by design (the
   `FLUTTER_XCODE_ARCHS` forwarding in build.py restricts Xcode to the host arch to
   match the cargo-built dylib). Do not try to produce a universal binary without
   also building the Rust side for both arches.
9. **Cargo needs network at build time** — dependency URLs point at upstream forks
   (`github.com/rustdesk-org/*`, documented carve-out). A fully air-gapped build
   would need those mirrored first.
10. **The `service` binary** — build.py copies `target/release/service` into the app
    bundle (`Contents/MacOS/service`). If `build.py --skip-cargo` is used, make sure
    that binary exists or the embedded service path will silently miss it.

## Quick troubleshooting table

| Symptom | Cause | Fix |
|---|---|---|
| vcpkg fails in aom/ffmpeg assembly | NASM 3.x installed | `brew uninstall nasm; brew install nasm@2 && brew link --force nasm@2` |
| `flutter_rust_bridge_codegen: command not found` | not installed for active toolchain | `cargo install flutter_rust_bridge_codegen --version 1.80.1 --features uuid --locked` |
| Dart errors referencing `generated_bridge.dart` | bridge not generated on this machine | run step 4 |
| Xcode build fails: no `liblibironfloor.dylib` | cargo step didn't run or wrong arch | run `cargo build --release` from repo root; confirm arm64 (`uname -m`) |
| App launches then exits; logs show module/class load errors | XIB customModule mismatch | verify `PRODUCT_NAME = IronFloor` in AppInfo.xcconfig; rebuild clean |
| Gatekeeper blocks app | unsigned binary | right-click → Open, or `xattr -cr IronFloor.app` |
| Update check does nothing | placeholder API/releases repos | expected until operator infra exists |
| TCC prompts name the wrong app | stale app copy in /Applications | remove old copies, reinstall fresh bundle, relaunch |
