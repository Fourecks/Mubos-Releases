# Mubos Releases

Public update channel for the Mubos desktop app. The source code is maintained privately in Fourecks/Mubos.

Manifests are published under `releases/stable` and `releases/beta`. Signed macOS and Windows packages are attached to GitHub Releases and never committed to this repository.

A manifest remains unpublished until a complete, signed release passes the release workflow.

## Windows downloads

GitHub Releases remains the immutable archive for signed packages. Netlify serves the current Windows MSIX and App Installer files from `https://mubos-downloads.netlify.app` with the MIME types required by Windows. The Netlify build reads each published Windows manifest, downloads the package from its immutable GitHub release URL in `source_url`, and regenerates the channel's App Installer XML.

The Netlify project uses `netlify.toml` and `scripts/build_windows_host.py`. Publishing a new Windows manifest on `main` triggers a Netlify build after the Netlify project is connected to this repository. Do not commit the generated `public/` output or `.netlify/` state.
