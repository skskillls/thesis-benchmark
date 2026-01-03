#!/bin/bash
# ============================================================================
# measure_build.sh - Metric Collection
# Uses /usr/bin/time for kernel-level precision, with fallback for minimal containers
# ============================================================================

set -e

TOOL=$1; SERVICE=$2; TYPE=$3; SCENARIO=$4; RUN_NUMBER=$5
shift 5

OUTPUT_DIR="${RESULTS_DIR:-${GITHUB_WORKSPACE:-$(pwd)}/results}"
mkdir -p "$OUTPUT_DIR"
RESULT_FILE="$OUTPUT_DIR/${TOOL}_${SERVICE}_${TYPE}_${SCENARIO}_run${RUN_NUMBER}.json"
METRICS_FILE=$(mktemp)
BUILD_LOG=$(mktemp)

echo "=== Benchmarking: $TOOL | $SERVICE | $TYPE | $SCENARIO | Run $RUN_NUMBER ==="

START_TIMESTAMP=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)

# ------------------------------------------------------------------
# GNU time vs. Fallback
# ------------------------------------------------------------------
USE_GNU_TIME=false

if command -v /usr/bin/time >/dev/null 2>&1; then
    if /usr/bin/time --version 2>&1 | grep -q "GNU"; then
        USE_GNU_TIME=true
    fi
elif [ -f /etc/alpine-release ] && command -v apk >/dev/null 2>&1; then
    echo "Installing GNU time for Alpine..."
    apk add --no-cache time >/dev/null 2>&1 || true
    command -v /usr/bin/time >/dev/null 2>&1 && USE_GNU_TIME=true
fi

# ------------------------------------------------------------------
# BUILD EXECUTION 
# ------------------------------------------------------------------
set +e

if [ "$USE_GNU_TIME" = true ]; then
    /usr/bin/time -f "real=%e\nmax_rss_kb=%M\ncpu_percent=%P\nuser_cpu=%U\nsys_cpu=%S" \
        -o "$METRICS_FILE" "$@" > "$BUILD_LOG" 2>&1
    BUILD_EXIT_CODE=$?
    
    DURATION=$(grep "^real=" "$METRICS_FILE" | cut -d'=' -f2)
    PEAK_MEM_KB=$(grep "^max_rss_kb=" "$METRICS_FILE" | cut -d'=' -f2)
    CPU_PERCENT=$(grep "^cpu_percent=" "$METRICS_FILE" | cut -d'=' -f2 | tr -d '%')
    USER_CPU=$(grep "^user_cpu=" "$METRICS_FILE" | cut -d'=' -f2)
    SYS_CPU=$(grep "^sys_cpu=" "$METRICS_FILE" | cut -d'=' -f2)
    
    PEAK_MEM_MB=$(awk "BEGIN {printf \"%.2f\", ${PEAK_MEM_KB:-0} / 1024}")
else
    echo "⚠️ GNU time not available. Using fallback."
    
    if date +%s.%N >/dev/null 2>&1; then
        START_TIME=$(date +%s.%N)
        "$@" > "$BUILD_LOG" 2>&1
        BUILD_EXIT_CODE=$?
        END_TIME=$(date +%s.%N)
        DURATION=$(awk "BEGIN {printf \"%.2f\", $END_TIME - $START_TIME}")
    else
        START_TIME=$(date +%s)
        "$@" > "$BUILD_LOG" 2>&1
        BUILD_EXIT_CODE=$?
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
    fi
    
    PEAK_MEM_MB=0; CPU_PERCENT=0; USER_CPU=0; SYS_CPU=0
fi
set -e

DURATION=${DURATION:-0}
PEAK_MEM_MB=${PEAK_MEM_MB:-0}
CPU_PERCENT=${CPU_PERCENT:-0}
USER_CPU=${USER_CPU:-0}
SYS_CPU=${SYS_CPU:-0}

cat "$BUILD_LOG"
BUILD_OUTPUT=$(cat "$BUILD_LOG")

# ------------------------------------------------------------------
# IMAGE SIZE
# ------------------------------------------------------------------
IMAGE_SIZE="N/A"; IMAGE_SIZE_BYTES=0

if command -v docker &>/dev/null; then
    IMAGE_SIZE=$(docker images benchmark-image:latest --format "{{.Size}}" 2>/dev/null | head -n1 || echo "N/A")
    IMAGE_SIZE_BYTES=$(docker image inspect benchmark-image:latest --format "{{.Size}}" 2>/dev/null || echo "0")
elif command -v buildah &>/dev/null; then
    IMAGE_SIZE=$(buildah images benchmark-image:latest --format "{{.Size}}" 2>/dev/null | head -n1 || echo "N/A")
fi

# ------------------------------------------------------------------
# CACHE HIT RATIO
# ------------------------------------------------------------------
CACHE_HITS=0
CACHE_TOTAL=1

case $TOOL in
    buildkit)
        CACHE_HITS=$(echo "$BUILD_OUTPUT" | grep -c "CACHED" 2>/dev/null || true)
        CACHE_TOTAL=$(echo "$BUILD_OUTPUT" | grep -cE "#[0-9]+" 2>/dev/null || true);;
    kaniko)
        CACHE_HITS=$(echo "$BUILD_OUTPUT" | grep -c "Using caching version" 2>/dev/null || true)
        CACHE_TOTAL=$(echo "$BUILD_OUTPUT" | grep -cE "(RUN|COPY|ADD|FROM)" 2>/dev/null || true);;
    buildah)
        CACHE_HITS=$(echo "$BUILD_OUTPUT" | grep -c "Using cache" 2>/dev/null || true)
        CACHE_TOTAL=$(echo "$BUILD_OUTPUT" | grep -cE "STEP" 2>/dev/null || true);;
esac

# Ensure numeric values (strip whitespace, default to 0/1)
CACHE_HITS=$(echo "$CACHE_HITS" | tr -d '[:space:]')
CACHE_TOTAL=$(echo "$CACHE_TOTAL" | tr -d '[:space:]')
CACHE_HITS=${CACHE_HITS:-0}
CACHE_TOTAL=${CACHE_TOTAL:-1}

# Ensure they are valid integers
if ! [[ "$CACHE_HITS" =~ ^[0-9]+$ ]]; then CACHE_HITS=0; fi
if ! [[ "$CACHE_TOTAL" =~ ^[0-9]+$ ]] || [ "$CACHE_TOTAL" -eq 0 ]; then CACHE_TOTAL=1; fi

CACHE_HIT_RATIO=$(awk "BEGIN {printf \"%.4f\", $CACHE_HITS / $CACHE_TOTAL}")

# ------------------------------------------------------------------
# JSON EXPORT
# ------------------------------------------------------------------
cat > "$RESULT_FILE" << EOF
{
  "tool": "$TOOL",
  "service": "$SERVICE",
  "dockerfile_type": "$TYPE",
  "cache_scenario": "$SCENARIO",
  "run_number": $RUN_NUMBER,
  "timestamp": "$START_TIMESTAMP",
  "ci_system": "${CI_SYSTEM:-local}",
  "performance": {
    "build_duration_seconds": $DURATION,
    "cpu_percent": $CPU_PERCENT,
    "cpu_user_seconds": $USER_CPU,
    "cpu_system_seconds": $SYS_CPU,
    "memory_peak_mb": $PEAK_MEM_MB,
    "image_size": "$IMAGE_SIZE",
    "image_size_bytes": $IMAGE_SIZE_BYTES,
    "cache_hits": $CACHE_HITS,
    "cache_total_steps": $CACHE_TOTAL,
    "cache_hit_ratio": $CACHE_HIT_RATIO
  },
  "exit_code": $BUILD_EXIT_CODE
}
EOF

echo "=== Result: ${DURATION}s | RAM: ${PEAK_MEM_MB}MB | CPU: ${CPU_PERCENT}% | Cache: ${CACHE_HIT_RATIO} ==="

rm -f "$METRICS_FILE" "$BUILD_LOG"
exit $BUILD_EXIT_CODE
