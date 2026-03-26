# ILIAS SAML/Shibboleth SSO Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan.

**Goal:** Configure ILIAS SSO using SAML/Shibboleth protocol with Keycloak as Identity Provider, since OIDC is not production-ready in ILIAS 9.18.

**Architecture:** Keycloak acts as SAML IdP → Shibboleth Service Provider (Apache mod_shib) → ILIAS built-in Shibboleth authentication → User logged in

**Tech Stack:** Keycloak (SAML IdP), Shibboleth SP (Apache mod_shib), ILIAS 9.18 (built-in Shibboleth support), Playwright (e2e testing)

---

## Critical Finding

**OIDC is NOT production-ready in ILIAS 9.18**

Research findings from ILIAS 9.18 deployment:
- OIDC library present but marked "maintenance requested"
- Feature wiki shows OIDC support is still in development
- Built-in SAML/Shibboleth support is production-ready and well-tested
- Forum threads confirm successful Keycloak → Shibboleth → ILIAS integrations

**Decision: Use SAML/Shibboleth instead of OIDC**

---

## Prerequisites

- [x] ILIAS deployed via Helm in opendesk namespace
- [x] Keycloak running with `opendesk` realm
- [x] LDAP group `managed-by-attribute-ILIAS` created
- [x] ILIAS accessible at https://lms.opendesk.example.com

---

## Phase 1: Keycloak SAML Configuration

### Task 1.1: Create Keycloak SAML Client for ILIAS

**Files:**
- Modify: `helmfile/apps/nubus/values-opendesk-keycloak-bootstrap.yaml.gotmpl`

- [ ] **Step 1: Add SAML client for ILIAS**

Add to the `clients` section:

```yaml
    {{ if true }}  # ILIAS SAML client - always configure
    - name: "ilias-saml"
      clientId: "ilias-saml"
      protocol: "saml"
      clientAuthenticatorType: "client-secret"
      secret: {{ .Values.secrets.keycloak.clientSecret.iliasSaml | quote }}
      redirectUris:
        - "https://lms.opendesk.example.com/*"
      rootUrl: "https://lms.opendesk.example.com"
      adminUrl: "https://lms.opendesk.example.com"
      attributes:
        saml.assertion.signature: "false"
        saml.force.post.binding: "true"
        saml.multivalued.roles: "false"
        saml.encrypt: "false"
        saml.server.signature: "true"
        saml.server.signature.keyinfo.ext: "false"
        saml.assertion.signature: "false"
        saml.client.signature: "false"
        saml.authnstatement: "true"
        saml_name_id_format: "persistent"
      protocolMappers:
        - name: "username"
          protocol: "saml"
          protocolMapper: "saml-user-property-mapper"
          consentRequired: false
          config:
            user.attribute: "uid"
            attribute.name: "username"
            attribute.nameformat: "Basic"
        - name: "email"
          protocol: "saml"
          protocolMapper: "saml-user-property-mapper"
          consentRequired: false
          config:
            user.attribute: "email"
            attribute.name: "email"
            attribute.nameformat: "Basic"
        - name: "firstname"
          protocol: "saml"
          protocolMapper: "saml-user-property-mapper"
          consentRequired: false
          config:
            user.attribute: "firstName"
            attribute.name: "firstname"
            attribute.nameformat: "Basic"
        - name: "lastname"
          protocol: "saml"
          protocolMapper: "saml-user-property-mapper"
          consentRequired: false
          config:
            user.attribute: "lastName"
            attribute.name: "lastname"
            attribute.nameformat: "Basic"
        - name: "role-list"
          protocol: "saml"
          protocolMapper: "saml-role-list-mapper"
          consentRequired: false
          config:
            single: "false"
            attribute.name: "Role"
            attribute.nameformat: "Basic"
    {{ end }}
```

- [ ] **Step 2: Generate SAML client secret**

Run: `openssl rand -base64 32`

- [ ] **Step 3: Add secret to configuration**

Modify: `helmfile/environments/hrz/secrets.yaml.gotmpl`

```yaml
secrets:
  keycloak:
    clientSecret:
      # ... existing secrets ...
      iliasSaml: "<GENERATED_SECRET>"
```

- [ ] **Step 4: Verify YAML syntax**

Run: `yamllint helmfile/apps/nubus/values-opendesk-keycloak-bootstrap.yaml.gotmpl`

- [ ] **Step 5: Commit**

```bash
git add helmfile/apps/nubus/values-opendesk-keycloak-bootstrap.yaml.gotmpl
git add helmfile/environments/hrz/secrets.yaml.gotmpl
git commit -m "feat: add ILIAS SAML client to Keycloak"
```

---

## Phase 2: Shibboleth Service Provider Configuration

### Task 2.1: Create Shibboleth SP ConfigMap

**Files:**
- Create: `helmfile/apps/ilias/templates/shibboleth-config.yaml`

- [x] **Step 1: Create Shibboleth SP configuration**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ilias-shibboleth-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "ilias.labels" . | nindent 4 }}
data:
  shibboleth2.xml: |
    <SPConfig xmlns="urn:mace:shibboleth:3.0:native:sp:config"
              xmlns:conf="urn:mace:shibboleth:3.0:native:sp:config"
              clockSkew="180">
      
      <OutOfProcess tranLogFormat="%u|%s|%IDP|%i|%ac|%t|%attr|%n|%b|%E|%S|%SS|%L|%ua|%m" />
      
      <SPLogger level="INFO" />
      
      <Listener baseLocation="/Shibboleth.sso" />
      
      <ISAPI normalizeRequest="true">
        <Site id="1" name="lms.opendesk.example.com"/>
      </ISAPI>
      
      <ApplicationDefaults entityID="https://lms.opendesk.example.com/shibboleth"
                           REMOTE_USER="eppn persistent-id targeted-id">
        
        <Sessions lifetime="28800" timeout="3600" relayState="ss:mem"
                  checkAddress="false" handlerSSL="true" cookieProps="https">
          
          <SSO discoveryProtocol="SAMLDS" ECP="true">
            SAML2 SAML1
          </SSO>
          
          <Logout>SAML2 Local</Logout>
          <Handler type="MetadataGenerator" Location="/Metadata" signing="false"/>
          <Handler type="Status" Location="/Status" acl="127.0.0.1"/>
          <Handler type="Session" Location="/Session" showAttributeValues="false"/>
          <Handler type="DiscoveryFeed" Location="/DiscoFeed"/>
        </Sessions>
        
        <MetadataProvider id="KeycloakMD" type="XML"
                          url="https://id.opendesk.example.com/realms/opendesk/protocol/saml/descriptor"
                          backingFilePath="keycloak-metadata.xml"
                          reloadInterval="7200">
        </MetadataProvider>
        
        <AttributeExtractor type="XML" validate="true" reloadChanges="false" path="attribute-map.xml"/>
        
        <AttributeResolver type="Query" subjectMatch="true">
          <Attribute name="username" nameFormat="Basic"/>
          <Attribute name="email" nameFormat="Basic"/>
          <Attribute name="firstname" nameFormat="Basic"/>
          <Attribute name="lastname" nameFormat="Basic"/>
          <Attribute name="Role" nameFormat="Basic"/>
        </AttributeResolver>
        
        <AttributeFilter type="XML" validate="true" path="attribute-policy.xml"/>
        
        <CredentialResolver type="File" use="signing"
                            key="sp-key.pem" certificate="sp-cert.pem"/>
        
      </ApplicationDefaults>
      
      <SecurityPolicyProvider type="XML" validate="true" path="security-policy.xml"/>
      <ProtocolProvider type="XML" validate="true" path="protocols.xml"/>
      
    </SPConfig>
  
  attribute-map.xml: |
    <Attributes xmlns="urn:mace:shibboleth:3.0:native:sp:attribute-map">
      <Attribute name="username" nameFormat="Basic" id="username"/>
      <Attribute name="email" nameFormat="Basic" id="email"/>
      <Attribute name="firstname" nameFormat="Basic" id="firstname"/>
      <Attribute name="lastname" nameFormat="Basic" id="lastname"/>
      <Attribute name="Role" nameFormat="Basic" id="role"/>
    </Attributes>
  
  attribute-policy.xml: |
    <AttributeFilterPolicyGroup xmlns="urn:mace:shibboleth:3.0:native:sp:attribute-filter">
      <PolicyRequirementRule xsi:type="ANY" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
      <AttributeRule attributeID="username">
        <PermitValueRule xsi:type="ANY" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
      </AttributeRule>
      <AttributeRule attributeID="email">
        <PermitValueRule xsi:type="ANY" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
      </AttributeRule>
      <AttributeRule attributeID="firstname">
        <PermitValueRule xsi:type="ANY" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
      </AttributeRule>
      <AttributeRule attributeID="lastname">
        <PermitValueRule xsi:type="ANY" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
      </AttributeRule>
    </AttributeFilterPolicyGroup>
```

- [x] **Step 2: Commit**

---

### Task 2.2: Generate Shibboleth SP Certificates

**Files:**
- Create: Kubernetes secret with SP certificates

- [x] **Step 1: Generate SP key and certificate**

Run:
```bash
openssl req -new -x509 -nodes -days 3650 \
  -keyout sp-key.pem \
  -out sp-cert.pem \
  -subj "/CN=lms.opendesk.example.com"
```

- [x] **Step 2: Create Kubernetes secret**

Run:
```bash
kubectl create secret generic ilias-shibboleth-certs \
  --from-file=sp-key.pem=sp-key.pem \
  --from-file=sp-cert.pem=sp-cert.pem \
  -n opendesk \
  --dry-run=client -o yaml > helmfile/apps/ilias/templates/shibboleth-certs-secret.yaml
```

- [x] **Step 3: Clean up local files**

Run: `rm sp-key.pem sp-cert.pem`

- [x] **Step 4: Commit**

---

## Phase 3: ILIAS Apache Configuration

### Task 3.1: Update ILIAS Deployment for Shibboleth

**Files:**
- Modify: ILIAS Helm values to enable Shibboleth

- [x] **Step 1: Update ILIAS values to mount Shibboleth config**

Modify the ILIAS Helm values to add Shibboleth configuration volumes:

```yaml
# Add to ilias values
extraVolumes:
  - name: shibboleth-config
    configMap:
      name: ilias-shibboleth-config
  - name: shibboleth-certs
    secret:
      secretName: ilias-shibboleth-certs

extraVolumeMounts:
  - name: shibboleth-config
    mountPath: /etc/shibboleth
    readOnly: true
  - name: shibboleth-certs
    mountPath: /etc/shibboleth/certs
    readOnly: true
```

- [x] **Step 2: Update Apache configuration to protect /shib_login.php**

Add to Apache site configuration (via ConfigMap or Helm values):

```apache
<Location /shib_login.php>
  AuthType shibboleth
  ShibRequestSetting requireSession 1
  require valid-user
</Location>
```

- [x] **Step 3: Commit**

---

## Phase 4: ILIAS Shibboleth Authentication Configuration

### Task 4.1: Configure ILIAS Shibboleth Settings via UI

**Goal:** Configure ILIAS to use Shibboleth authentication

- [ ] **Step 1: Access ILIAS administration**

1. Log into ILIAS at https://lms.opendesk.example.com
2. Navigate to: Administration → Authentication & Registration → Shibboleth

- [ ] **Step 2: Enable Shibboleth authentication**

Settings:
- **Enable Shibboleth**: Yes
- **Allow Shibboleth users to login**: Yes
- **Role selection**: Manual (default role: User)

- [ ] **Step 3: Configure Shibboleth settings**

**Shibboleth Settings:**
- **Login Link**: Show on login page
- **Login Page Title**: "Login with openDesk SSO"
- **Login Page Description**: "Use your openDesk credentials to access ILIAS"

**User Mapping:**
- **Username**: `username` (from Shibboleth attribute)
- **First Name**: `firstname`
- **Last Name**: `lastname`
- **Email**: `email`
- **External ID**: `username` (for user sync)

**Role Mapping:**
- **Default Role**: `il_user_role_std` (Standard user)
- **Update existing users**: Yes
- **Sync on each login**: Yes

- [ ] **Step 4: Save configuration**

- [ ] **Step 5: Document configuration**

Create: `docs/external-services/ilias-shibboleth-config.md`

```markdown
# ILIAS Shibboleth Configuration

## Settings Applied

### Shibboleth Authentication
- Enabled: Yes
- User creation: Automatic on first login
- User update: On each login

### Attribute Mapping
| ILIAS Field | Shibboleth Attribute | Keycloak Claim |
|-------------|---------------------|----------------|
| Username    | username            | uid            |
| Email       | email               | email          |
| First Name  | firstname           | firstName      |
| Last Name   | lastname            | lastName       |

### Role Assignment
- Default: `il_user_role_std` (Standard user)
- Manual role assignment per user

### Testing
1. Log out of ILIAS
2. Click "Login with openDesk SSO"
3. Redirects to Keycloak
4. After login, returns to ILIAS logged in
```

- [ ] **Step 6: Commit documentation**

```bash
git add docs/external-services/ilias-shibboleth-config.md
git commit -m "docs: add ILIAS Shibboleth configuration documentation"
```

---

## Phase 5: Portal Navigation Integration

### Task 5.1: Add ILIAS to Portal Navigation

**Files:**
- Determine actual portal navigation mechanism (from Phase 0 discovery)

- [ ] **Step 1: Add ILIAS navigation entry**

Based on discovery findings, ILIAS navigation entry should be added via UMC/Intercom configuration (exact mechanism TBD).

Navigation entry structure:

```json
{
  "id": "ilias",
  "title": {
    "de": "LMS",
    "en": "LMS"
  },
  "description": {
    "de": "Learning Management System",
    "en": "Learning Management System"
  },
  "target": "https://lms.opendesk.example.com/shib_login.php",
  "icon": "lms-icon",
  "order": 7,
  "allowedRoles": [
    "opendesk-ilias-access-control"
  ]
}
```

Note: Target URL points to `/shib_login.php` which triggers SAML SSO

- [ ] **Step 2: Create ILIAS icon**

Create: `helmfile/files/theme/portal/icons/lms-icon.svg` (if not already exists)

- [ ] **Step 3: Commit navigation changes**

```bash
git add <navigation-config-file> helmfile/files/theme/portal/icons/lms-icon.svg
git commit -m "feat: add ILIAS to portal navigation with SAML SSO"
```

---

## Phase 6: TDD - Test Implementation

### Task 6.1: Write E2E Test for ILIAS SAML SSO

**Files:**
- Create: `tests/e2e/ilias-saml-sso.spec.ts`

- [x] **Step 1: Write test for ILIAS SAML SSO from portal**

```typescript
import { test, expect } from '@playwright/test';

test.describe('ILIAS SAML SSO Authentication', () => {
  test('user can access ILIAS from portal via SAML SSO', async ({ page }) => {
    // Arrange: User logged into portal
    await page.goto('https://portal.opendesk.example.com/');
    
    // Log in to establish SSO session
    await page.fill('#username, input[name="username"]', 'ilias-test-user');
    await page.fill('#password, input[name="password"]', 'test-password');
    await page.click('#login-button, button[type="submit"]');
    await expect(page).toHaveURL(/portal\.opendesk\.hrz\.uni-marburg\.de/);

    // Act: Click ILIAS link in portal
    const iliasLink = page.locator('[data-entry="ilias"], a[href*="lms.opendesk"]');
    
    // Check if ILIAS link is visible (user should have ILIAS access)
    await expect(iliasLink).toBeVisible({ timeout: 10000 });
    
    await iliasLink.click();

    // Assert: Redirected to ILIAS Shibboleth login
    await expect(page).toHaveURL(/lms\.opendesk\.hrz\.uni-marburg\.de/, { timeout: 15000 });
    
    // Should trigger SAML SSO automatically
    // Keycloak SSO session should authenticate without password prompt
    
    // Verify user is logged into ILIAS
    await expect(page.locator('#il_user_id, .il-user-panel, [data-testid="user-display"]')).toBeVisible({ timeout: 10000 });
    
    // Verify NOT showing login form (SSO worked)
    await expect(page.locator('.il-login-form, #ilLoginForm')).not.toBeVisible();
  });

  test('user can access ILIAS directly via Shibboleth SSO', async ({ page }) => {
    // Arrange: User logged into portal (has SSO session)
    await page.goto('https://portal.opendesk.example.com/');
    await page.fill('#username, input[name="username"]', 'ilias-test-user');
    await page.fill('#password, input[name="password"]', 'test-password');
    await page.click('#login-button, button[type="submit"]');

    // Act: Navigate directly to ILIAS Shibboleth login
    await page.goto('https://lms.opendesk.example.com/shib_login.php');

    // Assert: SAML SSO authenticates user automatically
    await expect(page.locator('#il_user_id, .il-user-panel, [data-testid="user-display"]')).toBeVisible({ timeout: 10000 });
  });

  test('ILIAS session terminated on portal logout', async ({ page }) => {
    // Arrange: User logged into both portal and ILIAS
    await page.goto('https://portal.opendesk.example.com/');
    await page.fill('#username, input[name="username"]', 'ilias-test-user');
    await page.fill('#password, input[name="password"]', 'test-password');
    await page.click('#login-button, button[type="submit"]');
    
    // Access ILIAS to establish ILIAS session
    await page.goto('https://lms.opendesk.example.com/shib_login.php');
    await expect(page.locator('#il_user_id, .il-user-panel')).toBeVisible({ timeout: 10000 });

    // Act: Logout from portal
    await page.goto('https://portal.opendesk.example.com/');
    const logoutButton = page.locator('#logout-button, [data-testid="logout"]');
    await logoutButton.click();

    // Wait for logout to complete
    await expect(page).toHaveURL(/portal\.opendesk\.hrz\.uni-marburg\.de/, { timeout: 10000 });

    // Assert: ILIAS session terminated
    await page.goto('https://lms.opendesk.example.com/');
    await expect(page.locator('.il-login-form, #ilLoginForm')).toBeVisible({ timeout: 10000 });
  });

  test('user without ILIAS access cannot see ILIAS link', async ({ page }) => {
    // Arrange: User logged in WITHOUT managed-by-attribute-ILIAS group
    await page.goto('https://portal.opendesk.example.com/');
    await page.fill('#username, input[name="username"]', 'no-ilias-access-user');
    await page.fill('#password, input[name="password"]', 'test-password');
    await page.click('#login-button, button[type="submit"]');

    // Act: Check portal navigation for ILIAS link

    // Assert: ILIAS link should NOT be visible
    await expect(page.locator('[data-entry="ilias"], a[href*="lms.opendesk"]')).not.toBeVisible({ timeout: 5000 });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm run test:e2e tests/e2e/ilias-saml-sso.spec.ts`
Expected: FAIL (SAML not yet configured)

- [x] **Step 3: Commit tests**

---

## Phase 7: Deployment and Verification

### Task 7.1: Deploy Configuration Changes

- [ ] **Step 1: Apply Keycloak SAML client configuration**

Run: `helmfile -e hrz apply` (or relevant environment)

- [ ] **Step 2: Apply ILIAS Shibboleth configuration**

Run: `kubectl apply -f helmfile/apps/ilias/templates/shibboleth-config.yaml`
Run: `kubectl apply -f helmfile/apps/ilias/templates/shibboleth-certs-secret.yaml`

- [ ] **Step 3: Restart ILIAS pods to pick up new config**

Run: `kubectl rollout restart deployment/ilias-ilias -n opendesk`

- [ ] **Step 4: Wait for pods to be ready**

Run: `kubectl rollout status deployment/ilias-ilias -n opendesk --timeout=300s`

---

### Task 7.2: Manual Verification

- [ ] **Step 1: Test SAML SSO from portal**

1. Log into portal
2. Click ILIAS link
3. Verify redirected to ILIAS logged in (no password prompt)

- [ ] **Step 2: Test direct ILIAS access**

1. Navigate to https://lms.opendesk.example.com/shib_login.php
2. Verify SAML SSO authenticates automatically
3. Verify logged into ILIAS

- [ ] **Step 3: Test logout**

1. Logout from portal
2. Navigate to ILIAS
3. Verify session terminated (login form shown)

- [ ] **Step 4: Test access control**

1. Login as user without ILIAS group
2. Verify ILIAS link not visible in portal

---

### Task 7.3: Run E2E Tests

- [ ] **Step 1: Run ILIAS SAML SSO tests**

Run: `npm run test:e2e tests/e2e/ilias-saml-sso.spec.ts`
Expected: All tests PASS

- [ ] **Step 2: Run full test suite**

Run: `npm run test:e2e`
Expected: No regressions

---

## Phase 8: Documentation

### Task 8.1: Update User Documentation

- [x] **Step 1: Update user guide**

Update: `docs/external-services/user-guide.md`

Add section:
```markdown
## ILIAS Access

### From Portal
1. Log into openDesk portal
2. Click "LMS" tile
3. Automatically logged into ILIAS via SSO

### Direct Access
1. Navigate to https://lms.opendesk.example.com/shib_login.php
2. If logged into portal, automatically authenticated
3. If not logged in, redirected to Keycloak login

### Requirements
- Must be member of `managed-by-attribute-ILIAS` group
```

- [x] **Step 2: Commit**

---

### Task 8.2: Update Admin Documentation

- [x] **Step 1: Update admin guide**

- [x] **Step 2: Commit**

---

## Rollback Plan

If SAML integration fails:

1. **Disable Shibboleth authentication in ILIAS UI**
   - Navigate to: Administration → Authentication & Registration → Shibboleth
   - Disable Shibboleth login

2. **Remove ILIAS navigation from portal**
   - Delete navigation entry

3. **Fallback to local ILIAS authentication**
   - ILIAS will use local database authentication
   - No SSO integration

---

## Success Criteria

- [ ] ✅ ILIAS accessible via SAML SSO from portal
- [ ] ✅ Direct ILIAS access authenticates via SAML
- [ ] ✅ Portal logout terminates ILIAS session
- [ ] ✅ Access control enforced (navigation visibility)
- [ ] ✅ All E2E tests pass
- [ ] ✅ Documentation complete
- [ ] ✅ No regressions in existing functionality

---

**Implementation Plan Complete!** 🎉

Ready to execute using superpowers:executing-plans.