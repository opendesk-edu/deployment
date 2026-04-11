#!/bin/bash
# SPDX-FileCopyrightText: 2026 openDesk Edu Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Keycloak User Lifecycle Management Script
#
# This script automates user lifecycle management for HISinOne integration.
# Usage: ./keycloak-lifecycle.sh [create-user|disable-user|create-groups]
#

set -e

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-https://keycloak.opendesk.edu}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-master}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

# Get admin token
get_admin_token() {
    echo "Getting admin token..."
    TOKEN=$(curl -s -X POST \
        "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "client_id=admin-cli" \
        -d "username=${KEYCLOAK_ADMIN_USER}" \
        -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
        -d "grant_type=password" \
        | jq -r '.access_token')
    
    if [ -z "$TOKEN" ]; then
        echo "Error: Failed to get admin token"
        exit 1
    fi
    
    echo "$TOKEN"
}

# Create standard groups
create_groups() {
    echo "Creating Keycloak groups..."
    
    local TOKEN=$(get_admin_token)
    
    # Create base groups
    curl -s -X POST \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/groups" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{"name": "student"}'
    
    curl -s -X POST \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/groups" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{"name": "employee"}'
    
    curl -s -X POST \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/groups" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{"name": "lecturer"}'
    
    # Create faculty parent group
    curl -s -X POST \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/groups" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{"name": "faculty"}'
    
    echo "Groups created successfully"
}

# Create user
create_user() {
    local MATRICULATION_NUMBER="$1"
    local EMAIL="$2"
    local FIRST_NAME="$3"
    local LAST_NAME="$4"
    local GROUPS="${5:-student}"
    
    echo "Creating user: ${MATRICULATION_NUMBER}"
    
    local TOKEN=$(get_admin_token)
    
    # Get group IDs
    local GROUP_IDS=""
    IFS=',' read -ra USER_GROUPS <<< "$GROUPS"
    for GROUP in "${USER_GROUPS[@]}"; do
        local GROUP_ID=$(curl -s -X GET \
            "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/groups?search=${GROUP}" \
            -H "Authorization: Bearer ${TOKEN}" \
            | jq -r '.[0].id')
        
        if [ -n "$GROUP_IDS" ]; then
            GROUP_IDS="${GROUP_IDS},"
        fi
        GROUP_IDS="${GROUP_IDS}${GROUP_ID}"
    done
    
    # Create user
    local USER_ID=$(curl -s -X POST \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"${MATRICULATION_NUMBER}\",
            \"email\": \"${EMAIL}\",
            \"firstName\": \"${FIRST_NAME}\",
            \"lastName\": \"${LAST_NAME}\",
            \"enabled\": true,
            \"emailVerified\": true,
            \"groups\": [
                ${GROUP_IDS}
            ]
        }" \
        | jq -r '.id')
    
    echo "User created with ID: ${USER_ID}"
    echo "${USER_ID}"
}

# Disable user
disable_user() {
    local MATRICULATION_NUMBER="$1"
    
    echo "Disabling user: ${MATRICULATION_NUMBER}"
    
    local TOKEN=$(get_admin_token)
    
    # Get user ID
    local USER_ID=$(curl -s -X GET \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users?username=${MATRICULATION_NUMBER}" \
        -H "Authorization: Bearer ${TOKEN}" \
        | jq -r '.[0].id')
    
    if [ -z "$USER_ID" ]; then
        echo "Error: User not found: ${MATRICULATION_NUMBER}"
        exit 1
    fi
    
    # Disable user (don't delete - DSGVO compliance)
    curl -s -X PUT \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users/${USER_ID}" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "enabled": false,
            "emailVerified": false
        }'
    
    echo "User disabled: ${MATRICULATION_NUMBER}"
}

# Add user to faculty group
add_to_faculty() {
    local USER_ID="$1"
    local FACULTY="$2"
    
    echo "Adding user ${USER_ID} to faculty ${FACULTY}..."
    
    local TOKEN=$(get_admin_token)
    
    # Get faculty group ID
    local FACULTY_ID=$(curl -s -X GET \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/groups?search=faculty%2F${FACULTY}" \
        -H "Authorization: Bearer ${TOKEN}" \
        | jq -r '.[0].id')
    
    if [ -z "$FACULTY_ID" ]; then
        echo "Creating faculty group: ${FACULTY}"
        FACULTY_ID=$(curl -s -X POST \
            "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/groups" \
            -H "Authorization: Bearer ${TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"name\": \"faculty\", \"subGroups\": [{\"name\": \"${FACULTY}\"}]}" \
            | jq -r '.subGroups[0].id')
    fi
    
    # Add user to faculty group
    curl -s -X PUT \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users/${USER_ID}/groups/${FACULTY_ID}" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{}'
    
    echo "User added to faculty ${FACULTY}"
}

# Remove user from group
remove_from_group() {
    local USER_ID="$1"
    local GROUP="$2"
    
    echo "Removing user ${USER_ID} from group ${GROUP}..."
    
    local TOKEN=$(get_admin_token)
    
    # Get group ID
    local GROUP_ID=$(curl -s -X GET \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/groups?search=${GROUP}" \
        -H "Authorization: Bearer ${TOKEN}" \
        | jq -r '.[0].id')
    
    # Remove user from group
    curl -s -X DELETE \
        "${KEYCLOAK_URL}/admin/realms/${KEYCLOAK_REALM}/users/${USER_ID}/groups/${GROUP_ID}" \
        -H "Authorization: Bearer ${TOKEN}"
    
    echo "User removed from group ${GROUP}"
}

# Main function
main() {
    local COMMAND="$1"
    shift || true
    
    case "$COMMAND" in
        create-groups)
            create_groups
            ;;
        create-user)
            create_user "$@"
            ;;
        disable-user)
            disable_user "$@"
            ;;
        add-faculty)
            add_to_faculty "$@"
            ;;
        remove-group)
            remove_from_group "$@"
            ;;
        *)
            echo "Usage: $0 [create-groups|create-user|disable-user|add-faculty|remove-group]"
            echo "  create-groups                          Create standard groups"
            echo "  create-user MATRICULATION EMAIL FIRST LAST [GROUPS]"
            echo "  disable-user MATRICULATION_NUMBER"
            echo "  add-faculty USER_ID FACULTY"
            echo "  remove-group USER_ID GROUP_NAME"
            exit 1
            ;;
    esac
}

main "$@"