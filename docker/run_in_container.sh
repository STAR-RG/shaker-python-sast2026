#!/bin/bash
set -e

# Required: REPO_URL + either TEST_PATH (single) or TEST_ASSIGNMENTS (grouped)
# Optional: COMMIT_HASH, SR (default 20), NSR (default 10)

if [ -z "$REPO_URL" ]; then
    echo "ERROR: REPO_URL env var is required" >&2
    exit 1
fi

echo "==> Cloning $REPO_URL"
git clone --depth=100 "$REPO_URL" /project

if [ -n "$COMMIT_HASH" ]; then
    echo "==> Checking out $COMMIT_HASH"
    cd /project && git fetch --depth=100 origin "$COMMIT_HASH" && git checkout "$COMMIT_HASH"
fi

if [ -n "$EXTRA_DEPS" ]; then
    echo "==> Installing extra dependencies: $EXTRA_DEPS"
    pip install $(echo "$EXTRA_DEPS" | tr ';' ' ')
fi

# GROUPED MODE: TEST_ASSIGNMENTS lines are "test_path:::output_subpath"
if [ -n "$TEST_ASSIGNMENTS" ]; then
    n=$(echo "$TEST_ASSIGNMENTS" | wc -l)
    echo "==> Grouped mode: $n test(s)"
    MAX_EXIT=0
    set +e
    while read -r line; do
        [ -z "$line" ] && continue
        test_path="${line%%:::*}"
        output_subpath="${line#*:::}"
        echo "==> Running shaker on: $test_path"
        python3 /shaker/shaker.py pytest /project \
            -stp "$test_path" \
            -sr "${SR:-20}" \
            -nsr "${NSR:-10}" \
            -o "/output/$output_subpath"
        ec=$?
        echo "==> Exit $ec for: $test_path"
        if [ "$ec" -gt "$MAX_EXIT" ]; then MAX_EXIT=$ec; fi
    done <<< "$TEST_ASSIGNMENTS"
    echo "==> Done. Max exit code: $MAX_EXIT"
    EXIT_CODE=$MAX_EXIT

# SINGLE TEST MODE (legacy)
elif [ -n "$TEST_PATH" ]; then
    echo "==> Running shaker on $TEST_PATH (sr=${SR:-20} nsr=${NSR:-10})"
    set +e
    python3 /shaker/shaker.py pytest /project \
        -stp "$TEST_PATH" \
        -sr "${SR:-20}" \
        -nsr "${NSR:-10}" \
        -o /output
    EXIT_CODE=$?
    echo "==> Done. Results in /output/__results.json"

else
    echo "ERROR: Either TEST_PATH or TEST_ASSIGNMENTS must be set" >&2
    exit 1
fi

if [ -n "$HOST_UID" ] && [ -n "$HOST_GID" ]; then
    chown -R "$HOST_UID:$HOST_GID" /output
fi

exit $EXIT_CODE
