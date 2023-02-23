import argparse
import hashlib
import os
import platform
import re
import sys
import tarfile
import textwrap
import warnings
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

from packaging.version import parse as parse_version


def _read_checksums():
    """Read checksums from checksums.txt"""
    _checksum_file = Path(__file__).parent.joinpath("checksums.txt")
    checksums = {}
    with _checksum_file.open() as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            checksum, name = line.split()
            checksums[name] = checksum
    return checksums


checksums = _read_checksums()

machine_map = {
    "x86_64": "amd64",
}


def checksum_file(path):
    """Compute the sha256 checksum of a path"""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def install_traefik(prefix, plat, traefik_version):
    plat = plat.replace("-", "_")
    if "windows" in plat:
        traefik_archive_extension = "zip"
        traefik_bin = os.path.join(prefix, "traefik.exe")
    else:
        traefik_archive_extension = "tar.gz"
        traefik_bin = os.path.join(prefix, "traefik")

    traefik_archive = (
        "traefik_v" + traefik_version + "_" + plat + "." + traefik_archive_extension
    )
    traefik_archive_path = os.path.join(prefix, traefik_archive)

    traefik_url = (
        "https://github.com/traefik/traefik/releases"
        f"/download/v{traefik_version}/{traefik_archive}"
    )

    expected_checksum = checksums.get(traefik_archive, None)

    if os.path.exists(traefik_bin) and os.path.exists(traefik_archive_path):
        print("Traefik already exists")
        if expected_checksum is None:
            warnings.warn(
                f"Traefik {traefik_version} not tested!",
                stacklevel=2,
            )
            os.chmod(traefik_bin, 0o755)
            print("--- Done ---")
            return
        else:
            if checksum_file(traefik_archive_path) == expected_checksum:
                os.chmod(traefik_bin, 0o755)
                print("--- Done ---")
                return
            else:
                print(f"checksum mismatch on {traefik_archive_path}")
                os.remove(traefik_archive_path)

    print(f"Downloading traefik {traefik_version} from {traefik_url}...")
    urlretrieve(traefik_url, traefik_archive_path)

    if expected_checksum is not None:
        checksum = checksum_file(traefik_archive_path)
        if checksum != expected_checksum:
            raise OSError(f"Checksum failed {checksum} != {expected_checksum}")
    else:
        warnings.warn(
            f"Traefik {traefik_version} not tested!",
            stacklevel=2,
        )

    print("Extracting the archive...")
    if traefik_archive_extension == "tar.gz":
        with tarfile.open(traefik_archive_path, "r") as tar_ref:
            tar_ref.extract("traefik", prefix)
    else:
        with zipfile.ZipFile(traefik_archive_path, "r") as zip_ref:
            zip_ref.extract("traefik.exe", prefix)
    os.chmod(traefik_bin, 0o755)
    print(f"Installed {traefik_bin}")
    os.unlink(traefik_archive_path)
    print("--- Done ---")


def main():
    # extract supported and default versions from urls
    _version_pat = re.compile(r"v\d+\.\d+\.\d+")
    _versions = set()
    for filename in checksums:
        _versions.update(_version_pat.findall(filename))
    available_versions = sorted(_versions, key=parse_version, reverse=True)

    parser = argparse.ArgumentParser(
        description="Dependencies intaller",
        epilog=textwrap.dedent(
            f"""\
            Checksums available for traefik versions: {', '.join(available_versions)}
            """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--output",
        dest="installation_dir",
        default="./dependencies",
        help=textwrap.dedent(
            """\
            The installation directory (absolute or relative path).
            If it doesn't exist, it will be created.
            If no directory is provided, it defaults to:
            --- %(default)s ---
            """
        ),
    )

    machine = platform.machine()
    machine = machine_map.get(machine, machine)
    default_platform = f"{sys.platform}-{machine}"

    parser.add_argument(
        "--platform",
        dest="plat",
        default=default_platform,
        help=textwrap.dedent(
            """\
            The platform to download for.
            If no platform is provided, it defaults to:
            --- %(default)s ---
            """
        ),
    )

    parser.add_argument(
        "--traefik",
        action="store_true",
        help="DEPRECATED, IGNORED",
    )

    parser.add_argument(
        "--traefik-version",
        dest="traefik_version",
        default="2.9.8",
        help=textwrap.dedent(
            """\
            The version of traefik to download.
            If no version is provided, it defaults to:
            --- %(default)s ---
            """
        ),
    )
    if "--etcd" in sys.argv:
        sys.exit(
            "Installing etcd is no longer supported. Visit https://github.com/etcd-io/etcd/releases/"
        )
    if "--consul" in sys.argv:
        sys.exit(
            "Installing consul is no longer supported. Visit https://developer.hashicorp.com/consul/downloads"
        )

    args = parser.parse_args()
    deps_dir = args.installation_dir
    plat = args.plat
    traefik_version = args.traefik_version.lstrip("v")

    if args.traefik:
        print(
            "Specifying --traefik is deprecated and ignored. Only installing traefik is supported.",
            file=sys.stderr,
        )

    if os.path.exists(deps_dir):
        print(f"Using existing output directory {deps_dir}...")
    else:
        print(f"Creating output directory {deps_dir}...")
        os.makedirs(deps_dir)

    install_traefik(deps_dir, plat, traefik_version)


if __name__ == "__main__":
    main()
