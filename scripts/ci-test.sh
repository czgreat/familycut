#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${TEST_REPORT_DIR:-$ROOT_DIR/test-report}"
LOG_PATH="$REPORT_DIR/output.log"
PIP_INDEX_URL_CANDIDATES="${PIP_INDEX_URL_CANDIDATES:-${PIP_INDEX_URL:-https://mirrors.ustc.edu.cn/pypi/simple/} https://pypi.tuna.tsinghua.edu.cn/simple https://pypi.org/simple https://mirrors.aliyun.com/pypi/simple/}"
PIP_INSTALL_RETRIES="${PIP_INSTALL_RETRIES:-6}"
PIP_INSTALL_TIMEOUT="${PIP_INSTALL_TIMEOUT:-120}"
export APP_DATABASE_URL="${APP_DATABASE_URL:-sqlite:///$REPORT_DIR/familycut-test.db}"
export APP_MEDIA_ROOT="${APP_MEDIA_ROOT:-$REPORT_DIR/media}"
export APP_REPORT_IMAGE_ROOT="${APP_REPORT_IMAGE_ROOT:-$REPORT_DIR/reports}"

rm -rf "$REPORT_DIR"
mkdir -p "$REPORT_DIR"

echo "release_test_started_at=$(date -Iseconds)" > "$REPORT_DIR/summary.txt"

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "python/python3 not found" | tee -a "$LOG_PATH"
  exit 127
fi

PIP_ARGS=()
if "$PYTHON_BIN" -m pip install --help 2>/dev/null | grep -q -- "--break-system-packages"; then
  PIP_ARGS+=(--break-system-packages)
fi

run_pip_install() {
  local index_url="$1"
  shift
  PIP_INDEX_URL="$index_url" \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  "$PYTHON_BIN" -m pip install \
    "${PIP_ARGS[@]}" \
    --retries "$PIP_INSTALL_RETRIES" \
    --timeout "$PIP_INSTALL_TIMEOUT" \
    "$@" 2>&1 | tee -a "$LOG_PATH"
}

pip_install_with_fallback() {
  local label="$1"
  shift
  local index_url

  for index_url in $PIP_INDEX_URL_CANDIDATES; do
    echo "Trying $label via $index_url" | tee -a "$LOG_PATH"
    if run_pip_install "$index_url" "$@"; then
      return 0
    fi
    echo "Install failed for $label via $index_url" | tee -a "$LOG_PATH"
  done

  echo "All configured pip indexes failed for $label" | tee -a "$LOG_PATH"
  return 1
}

pip_install_with_fallback "bootstrap packages" --upgrade pip requests
pip_install_with_fallback "backend test dependencies" -e "$ROOT_DIR/backend" pytest pytest-cov

pytest "$ROOT_DIR/backend/tests" -q 2>&1 | tee -a "$LOG_PATH"

if command -v npm >/dev/null 2>&1; then
  (
    cd "$ROOT_DIR/admin-web"
    npm ci --no-audit --no-fund 2>&1 | tee -a "$LOG_PATH"
    npm run build 2>&1 | tee -a "$LOG_PATH"
  )
  (
    cd "$ROOT_DIR/mobile-web"
    npm ci --no-audit --no-fund 2>&1 | tee -a "$LOG_PATH"
    VITE_APP_BASE=/m/ npm run build 2>&1 | tee -a "$LOG_PATH"
  )
else
  echo "npm not found, skipping admin-web and mobile-web build" | tee -a "$LOG_PATH"
fi

if [ "${RUN_ANDROID_TEST_BUILD:-0}" = "1" ]; then
  if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
    echo "RUN_ANDROID_TEST_BUILD=1 but JAVA_HOME is not configured" | tee -a "$LOG_PATH"
    exit 1
  fi
  if [ -z "${ANDROID_SDK_ROOT:-}" ] || [ ! -d "${ANDROID_SDK_ROOT}" ]; then
    echo "RUN_ANDROID_TEST_BUILD=1 but ANDROID_SDK_ROOT is not configured" | tee -a "$LOG_PATH"
    exit 1
  fi

  export PATH="$JAVA_HOME/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH"
  export GRADLE_USER_HOME="${GRADLE_USER_HOME:-$REPORT_DIR/.gradle}"
  chmod +x "$ROOT_DIR/android-app/gradlew"

  (
    cd "$ROOT_DIR/android-app"
    ./gradlew :app:assembleDebug --console=plain 2>&1 | tee -a "$LOG_PATH"
  )
fi

if [ "${RUN_ANDROID_TEST_BUILD:-0}" = "1" ]; then
  if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
    echo "RUN_ANDROID_TEST_BUILD=1 but JAVA_HOME is not configured" | tee -a "$LOG_PATH"
    exit 1
  fi
  if [ -z "${ANDROID_SDK_ROOT:-}" ] || [ ! -d "${ANDROID_SDK_ROOT}" ]; then
    echo "RUN_ANDROID_TEST_BUILD=1 but ANDROID_SDK_ROOT is not configured" | tee -a "$LOG_PATH"
    exit 1
  fi

  export PATH="$JAVA_HOME/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH"
  export ANDROID_HOME="${ANDROID_HOME:-$ANDROID_SDK_ROOT}"
  export GRADLE_USER_HOME="${GRADLE_USER_HOME:-/root/.gradle}"
  chmod +x "$ROOT_DIR/android-app/gradlew"

  (
    cd "$ROOT_DIR/android-app"
    ./gradlew :app:assembleDebug --console=plain 2>&1 | tee -a "$LOG_PATH"
  )
fi

echo "release_test_finished_at=$(date -Iseconds)" >> "$REPORT_DIR/summary.txt"
