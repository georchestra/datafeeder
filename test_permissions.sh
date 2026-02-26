#!/bin/bash
set -e

GATEWAY="http://localhost:8080/datakern-backend"
DIRECT="http://localhost:8000"

DATASET_A="3f7cfed9-2c21-4ff9-9ebc-3ea9bba42937"
DATASET_B="a219a27f-7192-43ad-9e10-31c2835da7b0"
DATASET_C="48732035-2a1d-4360-8bd0-9addda43132c"

PASS=0
FAIL=0
BUGS=""

check() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $label (got $actual)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $label (expected $expected, got $actual)"
        FAIL=$((FAIL + 1))
        BUGS="$BUGS\n  - $label: expected $expected, got $actual"
    fi
}

gw_code() {
    curl -s -o /dev/null -w "%{http_code}" --user "$1:$1" "$GATEWAY$2"
}

direct_code() {
    curl -s -o /dev/null -w "%{http_code}" -H "sec-username: $1" -H "sec-org: $2" -H "sec-roles: $3" "$DIRECT$4"
}

echo ""
echo "=========================================="
echo "SCENARIO 2: Detail GET (METADATA_WRITE)"
echo "=========================================="
check "testadmin→DatasetA (admin+own)" "200" "$(gw_code testadmin "/ingestion/integrity-link/$DATASET_A")"
check "testadmin→DatasetC (admin)" "200" "$(gw_code testadmin "/ingestion/integrity-link/$DATASET_C")"
check "testuser→DatasetB (owner)" "200" "$(gw_code testuser "/ingestion/integrity-link/$DATASET_B")"
check "testuser→DatasetC (WRITE rule)" "200" "$(gw_code testuser "/ingestion/integrity-link/$DATASET_C")"
check "testuser→DatasetA (no perm)" "403" "$(gw_code testuser "/ingestion/integrity-link/$DATASET_A")"
check "idatafeeder→DatasetB (no perm)" "403" "$(direct_code idatafeeder idatafeeder ROLE_IMPORT "/ingestion/integrity-link/$DATASET_B")"

echo ""
echo "=========================================="
echo "SCENARIO 3: Rules GET/PUT (OWNER_ONLY)"
echo "=========================================="
check "testadmin→DatasetB rules GET (admin)" "200" "$(gw_code testadmin "/ingestion/integrity-link/$DATASET_B/rules")"
check "testuser→DatasetB rules GET (owner)" "200" "$(gw_code testuser "/ingestion/integrity-link/$DATASET_B/rules")"
check "testuser→DatasetC rules GET (WRITE≠owner)" "403" "$(gw_code testuser "/ingestion/integrity-link/$DATASET_C/rules")"
check "idatafeeder→DatasetC rules GET (owner)" "200" "$(direct_code idatafeeder idatafeeder ROLE_IMPORT "/ingestion/integrity-link/$DATASET_C/rules")"

echo ""
echo "=========================================="
echo "SCENARIO 4: Staging metadata GET (METADATA_WRITE)"
echo "=========================================="
check "testuser→DatasetB staging meta (owner)" "200" "$(gw_code testuser "/ingestion/staging/$DATASET_B/metadata")"
check "testuser→DatasetC staging meta (WRITE)" "200" "$(gw_code testuser "/ingestion/staging/$DATASET_C/metadata")"
check "idatafeeder→DatasetB staging meta (no perm)" "403" "$(direct_code idatafeeder idatafeeder ROLE_IMPORT "/ingestion/staging/$DATASET_B/metadata")"

echo ""
echo "=========================================="
echo "SCENARIO 5: Process POST (OWNER_ONLY) — 403 only"
echo "=========================================="
check "testuser→DatasetC process (WRITE≠owner)" "403" "$(curl -s -o /dev/null -w "%{http_code}" --user testuser:testuser -X POST "$GATEWAY/ingestion/process/" -H "Content-Type: application/json" -d "{\"integrity_link_id\": \"$DATASET_C\", \"title\": \"test\"}")"

echo ""
echo "=========================================="
echo "SCENARIO 6: Airflow events (OWNER_ONLY)"
echo "=========================================="
# Airflow events endpoint: /airflow/dags/{dag_id}/runs/{intlink_id} requires OWNER_ONLY
check "testuser→DatasetC events (WRITE≠owner)" "403" "$(direct_code testuser PSC ROLE_IMPORT "/airflow/dags/staging_dag/runs/$DATASET_C")"
check "idatafeeder→DatasetC events (owner)" "200" "$(direct_code idatafeeder idatafeeder ROLE_IMPORT "/airflow/dags/staging_dag/runs/$DATASET_C")"

echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
if [ $FAIL -gt 0 ]; then
    echo -e "  Bugs:$BUGS"
fi
