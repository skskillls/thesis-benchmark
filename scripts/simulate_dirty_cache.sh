#!/bin/bash
# ============================================================================
# simulate_dirty_cache.sh - Modifies mid-layer dependencies for dirty cache tests
# ============================================================================

SERVICE=$1
TIMESTAMP=$(date +%s)

if [ -z "$SERVICE" ]; then
    echo "Usage: $0 <service-name>"
    exit 1
fi

case $SERVICE in
    service-go)
        echo "// Dirty cache modification: $TIMESTAMP" >> "$SERVICE/main.go"
        echo "Modified $SERVICE/main.go"
        ;;
    service-node)
        sed -i.bak 's/"version": "1.0.0"/"version": "1.0.'$TIMESTAMP'"/' "$SERVICE/package.json"
        rm -f "$SERVICE/package.json.bak"
        echo "Modified $SERVICE/package.json version"
        ;;
    service-python)
        # Modify main.py instead of requirements.txt to avoid triggering pip install
        echo "# Dirty cache modification: $TIMESTAMP" >> "$SERVICE/main.py"
        echo "Modified $SERVICE/main.py"
        ;;
    *)
        echo "Unknown service: $SERVICE"
        exit 1
        ;;
esac

echo "Dirty cache modification applied to $SERVICE"
