# IronFloor Rebrand Plan

Branch: `ironfloor` (master left intact for the upstream GitHub fork).

Goal: ship an IronFloor release — Apple Silicon macOS first, all platforms rebranded —
with **zero** occurrences of the string `rustdesk` (any casing) in shipped artifacts:
Mach-O binaries, plists, resources, package metadata, and UI strings. The binary must
not be statically identifiable as RustDesk by EDR tooling (Falcon, CrowdStrike, ...).
Behavioral detection is out of scope; this plan removes every static identifier.

## 1. Identity mapping

| Old | New |
|---|---|
| `RustDesk` | `IronFloor` |
| `rustdesk` | `ironfloor` |
| `RUSTDESK` | `IRONFLOOR` |
| `com.carriez` (org) | `info.couto` |
| `com.carriez.rustdesk` / `com.carriez.flutterHbb` / `com.carriez.flutter_hbb` | `info.couto.ironfloor` |
| `rustdesk://` URL scheme | `ironfloor://` |
| `org.rustdesk.rustdesk/<...>` method channels | `info.couto.ironfloor/<...>` |
| crate `rustdesk`, lib `librustdesk` | crate `ironfloor`, lib `libironfloor` |
| `liblibrustdesk.dylib` / `.a` / `.so` / `.dll` | `liblibironfloor.dylib` / etc. |
| pubspec package `flutter_hbb` | `ironfloor` |
| `rs-ny.rustdesk.com` | `rs.couto.info` (placeholder, configure your server) |
| `api.rustdesk.com` version check | `api.couto.info` (placeholder) |
| `rustdesk.com/docs/...` links | `https://couto.info/docs/...` placeholders |
| `RS_PUB_KEY` (RustDesk public key) | placeholder for your own server key |
| `rustdesk-client` / `rustdesk-server` version types | `ironfloor-client` / `ironfloor-server` |
| `Purslane Tech Pte. Ltd.` copyright | `IronFloor (couto.info)` |

Note: changing bundle ID, launchd labels, and config/log paths means IronFloor installs
do not inherit RustDesk config/state — fresh identity by design, no migration code.

## 2. Submodule: hbb_common

`libs/hbb_common` is a git submodule of `rustdesk/hbb_common` and holds the two core
identity strings (`APP_NAME = "RustDesk"`, `ORG = "com.carriez"`), the default
rendezvous server, version-check URL, and `VER_TYPE_RUSTDESK_*`. The rebrand requires
editing it, so on this branch we **vendor it**: drop the submodule entry, commit its
contents as ordinary files, then edit. (Upstream-mirror rule in AGENTS.md is waived
here because this branch is the product, not a patch to feed upstream.)

## 3. Work items by phase

### Phase 1 — Core Rust identity
- `Cargo.toml`: package name `ironfloor`, lib name `libironfloor`, `default-run`,
  `authors`, `description`; `[package.metadata.winres]` ProductName/FileDescription/
  OriginalFilename; `[package.metadata.bundle]` name + identifier.
- `src/main.rs`: `use libironfloor::*`.
- `libs/hbb_common/src/config.rs`: `APP_NAME`, `ORG`, `RENDEZVOUS_SERVERS`,
  `RS_PUB_KEY`, doc links, `HELPER_URL` keys, `VER_TYPE_*` + version-check URL.
- `libs/hbb_common/src/lib.rs`: `VER_TYPE_RUSTDESK_CLIENT/_SERVER` values (protocol
  strings sent to your server — both sides must be IronFloor).
- Internal identifier sweep in `src/` + `libs/base` + `libs/scrap` etc.:
  `rustdesk_interval` / `RustDeskInterval` → `ironfloor_interval` / `IronFloorInterval`
  (symbol names land in the binary), `is_rustdesk()` → `is_ironfloor()`,
  `PORTABLE_APPNAME_RUNTIME_ENV_KEY` value `RUSTDESK_APPNAME` → `IRONFLOOR_APPNAME`,
  env `RUSTDESK_FORCED_DISPLAY_SERVER` → `IRONFLOOR_FORCED_DISPLAY_SERVER`,
  test/temp path literals (`rustdesk_read_all_test`, `rustdesk_validation_*`,
  `__RUSTDESK_SUDO_E_TEST_*`), `src/virtual_display_manager.rs` (`rustdesk_idd`,
  `IDD_IMPL_RUSTDESK`, platform-additions key `rustdesk_virtual_displays` — keep in
  sync with `kPlatformAdditionsRustDeskVirtualDisplays` in Dart).
- Exported FFI symbols (appear in the Mach-O dynamic symbol table; all callers updated
  in the same pass): `rustdesk_core_main`, `rustdesk_core_main_args`,
  `rustdesk_is_disable_installation`, `get_rustdesk_app_name` → `ironfloor_*`.
  Callers: `flutter/macos/Runner/MainFlutterWindow.swift`,
  `flutter/windows/runner/main.cpp`, `flutter/linux/main.cc`, Android JNI bridges,
  `src/platform/delegate.rs`, `src/naming.rs` output name.

### Phase 2 — macOS (Apple Silicon, priority)
- `flutter/macos/Runner.xcodeproj/project.pbxproj`: product `RustDesk.app` →
  `IronFloor.app` (file ref + productReference + scheme entries), the three
  `PRODUCT_BUNDLE_IDENTIFIER` values, `liblibrustdesk.dylib` refs (name + path).
- `flutter/macos/Runner/Configs/AppInfo.xcconfig`: `PRODUCT_NAME = IronFloor`,
  `PRODUCT_BUNDLE_IDENTIFIER = info.couto.ironfloor`, copyright.
- `flutter/macos/Runner/Info.plist`: `CFBundleURLName` → `info.couto.ironfloor`,
  `CFBundleURLSchemes` → `ironfloor`.
- `flutter/macos/Runner/Base.lproj/MainMenu.xib`: `customModule="RustDesk"` ×2.
- `flutter/macos/Runner/MainFlutterWindow.swift`: FFI symbol calls, plugin registrar
  name `RustDeskPlugin`, `NSLog("[RustDesk] ...")` strings, method channel name.
- `src/platform/macos.rs`: `/tmp/.rustdeskupdate-*`, `rustdesk_update.sh`,
  `rustdesk_root_update.log`, `/var/root/.rustdeskupdate_failed`,
  `/tmp/.rustdeskmount-*`, `com.carriez.{app}_service/_server` plist paths + labels
  (→ `info.couto....`), `correct_app_name()` replace targets, comments.
- `build.py` macOS path: dylib copy name, `IronFloor.app/Contents/MacOS/`,
  dmg volume/name (`ironfloor.dmg`, `IronFloor Installer`); keep the single-arch
  (arm64 on this host) dylib behavior.
- `res/osx-dist.sh`: artifact names, `--icon IronFloor.app`, etc.
- App icon: replace `flutter/macos/Runner/AppIcon.icns` + `res/*.svg` wordmark with
  IronFloor branding (new assets, no "rustdesk" text).

### Phase 3 — Flutter / Dart
- `flutter/pubspec.yaml`: `name: ironfloor`; every `package:flutter_hbb/...` import
  across `flutter/lib/**` (mechanical rename).
- Method channel names in `common.dart`, `input_model.dart`,
  `relative_mouse_model.dart`, `platform_channel.dart` (must match Phase 2 Swift and
  Linux C++).
- `flutter/lib/consts.dart`: `kPlatformAdditionsRustDeskVirtualDisplays`.
- `flutter/lib/models/native_model.dart` + web bridge + generated
  `bridge_generated.dart` / `bridge.dart`: `librustdesk.so` paths and generated
  symbols (regenerate with flutter_rust_bridge if output diverges).
- UI links (`rustdesk.com/pricing`, `/download`, docs) → couto.info placeholders.
- `flutter/lib/web/terminal_font.dart`: `rustdeskLocalFonts` JS global (rename on
  both sides of the web bridge).

### Phase 4 — Other platforms
- **Android**: applicationId/namespace `com.carriez.flutter_hbb` →
  `info.couto.ironfloor`, Kotlin package directory move
  `com/carriez/flutter_hbb` → `info/couto/ironfloor` (+ all `package`/`import`
  lines, manifest `package=`, broadcast actions, `DEBUG_BOOT_COMPLETED`),
  `strings.xml`, notification channel `RustDesk`/`RustDesk Service`/`RustDeskVD`,
  `rustdesk:wakelock`, `DEFAULT_NOTIFY_TITLE`, `rustdesk` scheme, NDK scripts.
- **iOS**: `flutter/ios/Runner.xcodeproj/project.pbxproj` (`liblibrustdesk.a`,
  bundle IDs, search paths), `Info.plist` (name, URL scheme),
  `exportOptions.plist` (provisioning profile key), bridging header symbols.
- **Linux**: `flutter/linux/CMakeLists.txt` (`BINARY_NAME`, `APPLICATION_ID`,
  `RUSTDESK_LIB`), `main.cc` (dlopen paths + `flutter_rustdesk_core_main`),
  `my_application.cc` (channels, icon name, window titles), `res/rustdesk.desktop`,
  `res/rustdesk-link.desktop` → `ironfloor*.desktop`, `res/rustdesk.service`,
  `res/PKGBUILD`, `res/rpm*.spec`, `appimage/*`, `flatpak/com.rustdesk.RustDesk.*`,
  `build.py` deb paths (`/usr/share/rustdesk`, `/usr/lib/rustdesk/libdrmtap.so.0`,
  `DRM_PACKAGE_NAME`, control file, `Conflicts/Replaces/Provides`).
- **Windows**: `flutter/windows/runner/main.cpp` (`librustdesk.dll`, typedefs),
  `res/msi/**` (WiX component `RustDesk.wxs` → `IronFloor.wxs`, `RuntimeBroker_rustdesk.exe`
  custom action, License.rtf privacy text, `preprocess.py`), `src/platform/windows.rs`
  portable/service strings, `libs/portable`, `libs/remote_printer`.

### Phase 5 — Localization (`src/lang/*.rs`, 55 files)
- Keys that are display text (`About RustDesk`, `Show RustDesk`,
  `Keep RustDesk background service`, `verify_rustdesk_password_tip`,
  `upgrade_rustdesk_server_pro_to_{}_tip`, `upgrade_remote_rustdesk_client_to_{}_tip`,
  `connecting_status` value, etc.): rename key + value consistently in **every** file
  including `template.rs` and `en.rs` (per the localization rules a renamed key must
  change in all files at once; no new keys are added).
- Values in all languages: `RustDesk` → `IronFloor` (translations untouched otherwise).
- Documented exception: `it.rs` is normally maintainer-locked; the brand token itself
  is replaced identically everywhere, nothing else is touched.

### Phase 6 — Repo, docs, CI
- README.md, docs/**, fastlane metadata, CLAUDE.md/GEMINI.md/AGENTS.md note.
- `.github/workflows/*`: artifact names (`rustdesk.sbom.json` → `ironfloor.sbom.json`),
  workflow titles. Keep build logic intact.
- `res/job.py`, `res/ab.py`, `Dockerfile`, `entrypoint.sh`, `examples/`.

### Phase 7 — Build & verification (the gate)
1. `cargo build --release` on arm64 macOS; `flutter build macos --release` via
   `build.py` flow with `FLUTTER_XCODE_ARCHS=arm64`.
2. Artifact inspection gate (must be 0 hits):
   - `strings` (case-insensitive: `rustdesk`, `carriez`, `purslane`, `RustDesk`) over
     every Mach-O in `IronFloor.app` (main exe, `liblibironfloor.dylib`, `service`,
     Flutter frameworks, embedded dylibs).
   - `nm -gU` on exported symbols — no `rustdesk*` dynsyms.
   - `plutil -p` over Info.plist + generated LaunchDaemon/LaunchAgent plists.
   - `codesign -d --entitlements -` and bundle tree walk for file/dir names.
3. Repo-wide `grep -ri` audit (excluding allowed carve-outs below), plus
   `strings` audit of the deb/rpm payloads for the Linux rebrand.
4. Functional smoke test on macOS: launch GUI, grant permissions (TCC prompts show
   "IronFloor"), connect two instances via your own rendezvous server
   (`rs.couto.info` placeholder), URL scheme `ironfloor://` opens the app,
   launchd labels under `info.couto.ironfloor`.

## 4. Allowed remaining occurrences (documented carve-outs)

These contain "rustdesk" but never reach shipped artifacts:

1. **Dependency source URLs** — `github.com/rustdesk-org/*` and `rustdesk/hbb_common`
   in `Cargo.toml`, `pubspec.yaml`, lockfiles. Renaming breaks the build; they are
   fetch-time only. (Optional hardening: mirror those repos under couto and repoint.)
2. **Upstream issue-link comments** (`// https://github.com/rustdesk/rustdesk/issues/...`)
   in code comments — traceability to upstream fixes, not compiled into binaries.
   Kept verbatim; prose around them is swept.
3. Git history and this plan file itself.

Everything else — binaries, plists, resources, packages, UI strings — must be clean.

## 5. Regression surface

- Existing behavior changes only where identity changes (paths, labels, scheme,
  protocol version strings). Capture/protocol/input code paths untouched.
- Mixed fleets (RustDesk ↔ IronFloor) will not interoperate via the default public
  rendezvous server after `RS_PUB_KEY`/server swaps — intended, since B2B deployments
  run their own server.
- `git merge master` from upstream will conflict heavily in swept files; expected.
