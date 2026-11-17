#!/usr/bin/env python3
"""Build Windows App Installer channels from immutable GitHub Releases assets."""
import json
import os
import re
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
REPO = "Fourecks/Mubos-Releases"
ORIGIN = os.environ.get("MUBOS_WINDOWS_DOWNLOAD_ORIGIN", "https://mubos-downloads.netlify.app").rstrip("/")
APP_ID = "com.sitolab.mubos"
APP_NS = "http://schemas.microsoft.com/appx/appinstaller/2017"
S4_NS = "http://schemas.microsoft.com/appx/appinstaller/2021"

def download(url, destination):
    if not url.startswith(f"https://github.com/{REPO}/releases/download/"):
        raise ValueError(f"Refusing non-release asset URL: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "Mubos-Release-Host/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)

def package_identity(package):
    with zipfile.ZipFile(package) as archive:
        root = ET.fromstring(archive.read("AppxManifest.xml"))
    identity = root.find("{*}Identity")
    if identity is None or identity.attrib.get("Name") != APP_ID:
        raise ValueError(f"Package identity mismatch: {package}")
    return identity.attrib

def appinstaller(channel, identity):
    ET.register_namespace("", APP_NS)
    ET.register_namespace("s4", S4_NS)
    version = identity["Version"]
    app_uri = f"{ORIGIN}/{channel}/Mubos.appinstaller"
    root = ET.Element(f"{{{APP_NS}}}AppInstaller", {
        "Uri": app_uri, "Version": version, "IgnorableNamespaces": "s4",
    })
    ET.SubElement(root, f"{{{APP_NS}}}MainPackage", {
        "Name": identity["Name"], "Publisher": identity["Publisher"],
        "Version": version,
        "ProcessorArchitecture": identity.get("ProcessorArchitecture", "x64"),
        "Uri": f"{ORIGIN}/{channel}/Mubos.msix",
    })
    settings = ET.SubElement(root, f"{{{APP_NS}}}UpdateSettings")
    launch = ET.SubElement(settings, f"{{{APP_NS}}}OnLaunch")
    launch.set(f"{{{S4_NS}}}HoursBetweenUpdateChecks", "24")
    launch.set(f"{{{S4_NS}}}ShowPrompt", "true")
    launch.set(f"{{{S4_NS}}}UpdateBlocksActivation", "false")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

def build():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for channel in ("beta", "stable"):
        manifest_path = ROOT / "releases" / channel / "windows.json"
        metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not metadata.get("published"):
            continue
        source = metadata.get("source_url")
        if not source:
            source = metadata.get("download_url", "")
            if "mubos-downloads.netlify.app" in source:
                raise ValueError(f"{manifest_path} needs source_url for GitHub's immutable MSIX asset.")
        package = PUBLIC / channel / "Mubos.msix"
        package.parent.mkdir(parents=True, exist_ok=True)
        certificate_url = metadata.get("certificate_url") or re.sub(r"/Mubos\.msix(?:\?.*)?$", "/Mubos-Development.cer", source)
        cert = PUBLIC / channel / "Mubos-Development.cer"
        download(source, package)
        download(certificate_url, cert)
        identity = package_identity(package)
        if int(metadata.get("build", 0)) != int(identity["Version"].split(".")[-1]):
            raise ValueError(f"Build number differs between manifest and MSIX for {channel}.")
        (package.parent / "Mubos.appinstaller").write_bytes(appinstaller(channel, identity))
        print(f"Prepared {channel} Mubos {identity['Version']} ({package.stat().st_size} bytes).")
    (PUBLIC / "_headers").write_text(
        "/*/*.json\n  Content-Type: application/json\n"
        "/beta/*.appinstaller\n  Content-Type: application/appinstaller\n  Cache-Control: no-store\n"
        "/beta/*.msix\n  Content-Type: application/msix\n  Cache-Control: no-store\n"
        "/beta/*.cer\n  Content-Type: application/pkix-cert\n  Cache-Control: no-store\n"
        "/stable/*.appinstaller\n  Content-Type: application/appinstaller\n  Cache-Control: no-store\n"
        "/stable/*.msix\n  Content-Type: application/msix\n  Cache-Control: no-store\n"
        "/stable/*.cer\n  Content-Type: application/pkix-cert\n  Cache-Control: no-store\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    build()
