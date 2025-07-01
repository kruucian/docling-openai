#!/usr/bin/env bash
set -euo pipefail

# Parse command-line arguments for --dryrun, --cert and --verbose early
dryrun=false
cert_mode=false
verbose=false
for arg in "$@"; do
    case "$arg" in
        --dryrun) dryrun=true ;;
        --cert)  cert_mode=true ;;
        --verbose) verbose=true ;;
    esac
done

# Helper function for verbose logging
vlog() {
    if [ "$verbose" = true ]; then
        echo "$@"
    fi
}

# Add repo assignment early to avoid unbound variable error.
# Determine repository root (directory that contains this script).
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
vlog "Repo set to: $repo"

# -----------------------------------------------------------------------------
# Derive project-specific virtual environment name.
# The venv directory will be named using the convention `venv-<foldername>` where
# `<foldername>` is the basename of the repository path.  For example, running
# the script from a folder called `scrapper` will result in a venv folder named
# `venv-scrapper`.
# -----------------------------------------------------------------------------

project_basename="$(basename "$repo")"
# Replace potential whitespace with underscores to form a safe directory name.
project_basename="${project_basename// /_}"
venv_name="venv-${project_basename}"
vlog "Using virtual environment directory name: $venv_name"

# Use the dynamic virtual environment directory throughout the script.
venv_dir="$repo/$venv_name"

# Detect cluster environment by checking for cluster init script (moved earlier)
cluster_init="/arm/tools/setup/init/bash"
if [ -f "$cluster_init" ]; then
  echo "Cluster environment detected."
  is_cluster=true
  vlog "Cluster init script found at $cluster_init"
else
  echo "Local environment detected."
  is_cluster=false
  vlog "No cluster init script found; running locally."
fi

# For local environment, check that python3.13 is installed.
if [ "$is_cluster" = false ]; then
    if ! command -v python3.13 >/dev/null 2>&1; then
        echo "python3.13 is not installed on local system. Please install python3.13 and try again."
        exit 1
    else
        vlog "python3.13 found on local system."
    fi
fi

# After module load, in cluster check that python3.13 is the correct version.
if [ "$is_cluster" = true ]; then
    version=$(python3.13 -V 2>&1)
    if [[ "$version" != *"3.13"* ]]; then
        echo "Cluster python3.13 not found or wrong version. Please check module load."
        exit 1
    else
        vlog "Cluster python3.13 version confirmed: $version"
    fi
fi

# --- Cert Management with certifi integration (runs always) ---
arm_cert_url="https://artifactory.arm.com/artifactory/vault.pki/ent-pki/pem/certs/ARM%20Enterprise%20PKI%20Root%20CA.pem"
echo "Downloading Arm Enterprise PKI Root CA certificate from:"
echo "$arm_cert_url"
# Ensure cert directory exists
if [ ! -d "$repo/cert" ]; then
    echo "Cert folder not found. Creating cert folder at $repo/cert"
    mkdir -p "$repo/cert"
    vlog "Created cert folder at $repo/cert"
else
    vlog "Cert folder at $repo/cert already exists; skipping creation."
fi
cert_dir="$repo/cert"
arm_cert_path="$cert_dir/Arm_Enterprise_PKI_Root_CA.pem"

if [ "$dryrun" = true ]; then
    echo "[DRYRUN] Would download certificate to $arm_cert_path"
else
    curl --retry 5 -f -s "$arm_cert_url" -o "$arm_cert_path"
    vlog "Downloaded certificate to $arm_cert_path"
fi

# Ensure pip is installed (always check irrespective of dryrun)
if ! python3.13 -m pip --version > /dev/null 2>&1; then
    echo "pip not found, installing pip via ensurepip..."
    python3.13 -m ensurepip --upgrade
    vlog "pip installed via ensurepip."
else
    vlog "pip is already installed."
fi

# Ensure certifi is installed
if [ "$dryrun" = true ]; then
    echo "[DRYRUN] Would check and install certifi if needed"
else
    if ! python3.13 -c "import certifi" 2>/dev/null; then
        echo "certifi not found. Attempting installation to the user site-packages..."

        # Homebrew and some Linux distributions mark their system Python as
        # "externally-managed" (PEP 668) which blocks global package
        # installations.  The official guidance is to use either the user
        # site or a virtual environment.  We try the user site first with the
        # additional "--break-system-packages" flag (ignored by older
        # Pythons).  If that still fails – for example, because the platform
        # forbids even the user install – we fall back to creating a dedicated
        # virtual environment inside the repository and install certifi there.

        if python3.13 -m pip install --user --break-system-packages certifi; then
            vlog "certifi successfully installed to user site-packages."
        else
            echo "User-site installation failed (possibly due to PEP 668 enforcement). Falling back to a repository-local virtual environment."

            # Create the fallback venv only if it does not exist yet.
            if [ ! -d "$venv_dir" ]; then
                echo "Creating fallback virtual environment at $venv_dir"
                python3.13 -m venv "$venv_dir"
                vlog "Fallback virtual environment created at $venv_dir"
            else
                vlog "Fallback virtual environment already exists at $venv_dir"
            fi

            # Activate the venv *inside* the current shell so that the rest of
            # the script sees the updated PATH and PYTHONHOME.
            # shellcheck disable=SC1090
            source "$venv_dir/bin/activate"

            echo "Installing certifi inside fallback virtual environment..."
            if ! python -m pip install --upgrade pip certifi; then
                echo "Failed to install certifi inside the fallback virtual environment." >&2
                exit 1
            fi

            vlog "certifi installed inside fallback virtual environment."
        fi
    else
        vlog "certifi is already available."
    fi
fi

# Retrieve certifi CA bundle path with error handling (skip entirely for dry-run)
if [ "$dryrun" = true ]; then
    echo "[DRYRUN] Would retrieve certifi bundle path and reinstall certifi if necessary"
    # Provide a placeholder path so later references do not fail during dry-run.
    certifi_bundle="/path/to/certifi/cacert.pem"
else
    if ! certifi_bundle=$(python3.13 -c "import certifi; print(certifi.where())" 2>/dev/null); then
        echo "Error retrieving certifi bundle. Reinstalling certifi..."
        python3.13 -m pip install --upgrade --force-reinstall certifi
        certifi_bundle=$(python3.13 -c "import certifi; print(certifi.where())")
        vlog "Reinstalled certifi; new certifi bundle at $certifi_bundle"
    else
        vlog "Using certifi bundle at $certifi_bundle"
    fi
fi

# For cluster environment, always use the venv's certifi bundle
if [ "$is_cluster" = true ]; then
    if [ ! -d "$venv_dir" ]; then
        echo "Cluster venv not found, creating it..."
        python3.13 -m venv "$venv_dir"
        vlog "Created cluster virtual environment at $venv_dir"
    else
        vlog "Cluster venv found at $venv_dir, skipping creation."
    fi
    echo "Activating cluster virtual environment..."
    source "$venv_dir/bin/activate"
    certifi_bundle=$(python -c "import certifi; print(certifi.where())")
    echo "Using cluster venv certifi bundle at $certifi_bundle"
    vlog "Cluster venv activated and certifi bundle used from venv."
else
    # For local environment, if system bundle is not writable then use venv
    if [ ! -w "$certifi_bundle" ]; then
        echo "System certifi bundle not writable, switching to virtual environment update."
        if [ ! -d "$venv_dir" ]; then
            echo "Virtual environment not found, creating it..."
            python3.13 -m venv "$venv_dir"
            vlog "Created virtual environment at $venv_dir"
        else
            vlog "Virtual environment found at $venv_dir, skipping creation."
        fi
        source "$venv_dir/bin/activate"
        certifi_bundle=$(python -c "import certifi; print(certifi.where())")
        echo "Using venv certifi bundle at $certifi_bundle"
        vlog "Local venv activated and certifi bundle used from venv."
    else
        vlog "System certifi bundle is writable; using system bundle."
    fi
fi

# Append downloaded certificate to certifi bundle if not already present
if [ "$dryrun" = true ]; then
    echo "[DRYRUN] Would check and append certificate to certifi bundle if needed"
else
    if ! grep -Fq "PKI Root CA" "$certifi_bundle"; then
        echo "Appending downloaded certificate to certifi bundle at $certifi_bundle"
        cat "$arm_cert_path" >> "$certifi_bundle"
        vlog "Certificate appended to certifi bundle."
    else
        vlog "Certificate already present in certifi bundle; skipping append."
    fi
fi

# Export the certificate environment variables to use the updated certifi bundle
export SSL_CERT_FILE="$certifi_bundle"
export NODE_EXTRA_CA_CERTS="$certifi_bundle"
echo "Exported SSL_CERT_FILE and NODE_EXTRA_CA_CERTS as:"
echo "  SSL_CERT_FILE=$SSL_CERT_FILE"
echo "  NODE_EXTRA_CA_CERTS=$NODE_EXTRA_CA_CERTS"

# -----------------------------------------------------------------------------
# Ensure the virtual environment *also* contains the Arm root certificate.
# The logic above may have modified the system-level certifi bundle when the
# local environment considered it writable.  However, the nova launcher
# (bin/nova) always activates the repository-local virtual environment and
# relies on that venv's certifi bundle via `certifi.where()`.  Therefore we
# must guarantee that the certificate is present in the venv even when the
# earlier logic decided to operate on the system bundle.
# -----------------------------------------------------------------------------

if [ -n "${VENV:-}" ] && [ -f "$VENV/bin/activate" ] && [ "$dryrun" != true ]; then
    # Activate the venv in a subshell to avoid polluting the current shell
    (
        # shellcheck disable=SC1090
        source "$VENV/bin/activate"
        venv_certifi_bundle=$(python - <<'PY'
import certifi, sys
print(certifi.where())
PY
        )

        if ! grep -Fq "PKI Root CA" "$venv_certifi_bundle"; then
            echo "Appending downloaded certificate to venv certifi bundle at $venv_certifi_bundle"
            cat "$arm_cert_path" >> "$venv_certifi_bundle"
            vlog "Certificate appended to venv certifi bundle."
        else
            vlog "Certificate already present in venv certifi bundle; skipping append."
        fi
    )
fi

# If --cert flag was passed, then run cert logic only.
if [ "$cert_mode" = true ]; then
    echo "CERT management completed. Exiting as --cert flag was provided."
    exit 0
fi

# Load required modules on cluster
if [ "$is_cluster" = true ]; then
  python_module="python/python/3.13.0"
  echo "Loading modules: core eda swdev util $python_module arm/cluster"
  if ! module load core eda swdev util "$python_module" arm/cluster; then
    echo "Failed to load $python_module. Searching for latest available python module..."
    candidates=$(mgrep python/python/3.13 || true)
    if [ -z "$candidates" ]; then
      echo "No python/python/3.13 modules found." >&2
      exit 1
    fi
    latest=$(echo "$candidates" | sort -V | tail -n1)
    echo "Loading $latest"
    module load "$latest"
  fi
  echo "Cluster module loading complete."
else
  echo "Skipping module loading on local environment."
fi

# Set up virtual environment path
if [ "$is_cluster" = true ]; then
    read -p "Enter your scratch directory path if available, otherwise press enter to install locally: " user_scratch
    if [ -n "$user_scratch" ]; then
        scratch_base="$user_scratch"
        scratch_venv_base="$scratch_base/venv"
        scratch_venv="$scratch_venv_base/$venv_name"
        # If the venv already exists in scratch, output message and skip creation.
        if [ -d "$scratch_venv" ]; then
            echo "Virtual environment already exists at $scratch_venv, skipping creation."
            vlog "Virtual environment already exists at $scratch_venv, skipping creation."
        else
            echo "Creating virtual environment directory at $scratch_venv."
            mkdir -p "$scratch_venv"
            vlog "Created virtual environment directory at $scratch_venv."
        fi
        ln -sfn "$scratch_venv" "$venv_dir"
        export VENV="$scratch_venv"
        vlog "Linked scratch virtual environment to $venv_dir"
    else
        read -p "No scratch provided. Install virtual environment locally? (y/N): " answer
        if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
            echo "Aborted."
            exit 1
        fi
        export VENV="$venv_dir"
        vlog "Set VENV to local venv at $venv_dir"
    fi
else
    export VENV="$venv_dir"
    vlog "Set VENV to repo venv at $venv_dir"
fi

# Create the venv if it does not yet exist
if [ -f "$VENV/bin/activate" ]; then
  echo "Using existing Python 3.13 virtual environment at $VENV (already exists, skipping creation)."
  vlog "Existing virtual environment found at $VENV"
else
  echo "Creating Python 3.13 virtual environment at $VENV"
  python3.13 -m venv "$VENV"
  vlog "Virtual environment created at $VENV"
fi

echo "Activating virtual environment"
# shellcheck disable=SC1090
source "$VENV/bin/activate"
echo "Virtual environment activated."

echo "Upgrading pip and installing dependencies"
if [ "$dryrun" = true ]; then
    echo "[DRYRUN] Skipping pip upgrade and installation commands"
else
    python3.13 -m ensurepip --upgrade
    python3.13 -m pip install --upgrade pip
    python3.13 -m pip install -r requirements.txt
    vlog "Upgraded pip and installed dependencies from requirements.txt"
fi

echo "Virtual environment setup complete."