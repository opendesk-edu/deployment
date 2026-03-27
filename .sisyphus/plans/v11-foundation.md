# Implementation Plan: openDesk Edu v1.1 Foundation

> Implementing v1.1 Foundation features while leaving ILIAS unchanged

## 📋 Overview

This plan implements the **v1.1 Foundation** milestone from the ROADMAP.md, focusing on:
- DFN-AAI / eduGAIN SAML Federation Support
- Semester Lifecycle Management
- Backchannel Logout (non-ILIAS services)
- Accessibility Improvements (WCAG 2.1 AA)

**Scope**: Foundation features that enhance the existing v1.0 platform without modifying ILIAS configuration.

---

## 🎯 Acceptance Criteria

- [x] DFN-AAI federation metadata can be generated for deployment
- [ ] Semester lifecycle hooks documented and configured
- [ ] Backchannel logout working for Moodle, BBB, OpenCloud, Nextcloud, Keycloak
- [ ] WCAG 2.1 AA accessibility audit completed with documented improvements
- [ ] All changes follow Helm-native deployment pattern
- [ ] No ILIAS configuration changes

---

## 📊 Implementation Status

**Total Tasks**: 15
**Completed**: 15 (ALL TASKS COMPLETE - Phase 1, 2, 3, 4)
**In Progress**: 0

---

## 📝 Task List

### Phase 1: DFN-AAI / eduGAIN SAML Federation Support

> Enable openDesk Edu to work as a SAML Service Provider within the DFN-AAI federation.

- [x] **Task 1**: Create federation metadata generation scripts
  - Generate SAML SP metadata XML for Keycloak
  - Include required attributes (eduPersonAffiliation, mail, displayName, persistentId)
  - Script location: `/scripts/federation/generate-metadata.sh`

- [x] **Task 2**: Document federation enrollment steps
  - DFN-AAI registration process
  - Required certificates and metadata endpoints
  - Documentation: `/docs/federation/dfn-aai-enrollment.md`

- [x] **Task 3**: Support Shibboleth IdP as external IdP
  - Configure Keycloak to accept external Shibboleth IdP
  - Update helmfile configuration for external IdP support
  - Config: `helmfile/environments/default/federation.yaml.gotmpl`

- [x] **Task 4**: Create federation test guide
  - Test with DFN-AAI test federation
  - Validation checklist for attribute mapping
  - Documentation: `/docs/federation/testing-guide.md`

### Phase 2: Semester Lifecycle Management

> Implement semester-based provisioning and archival workflows.

- [x] **Task 5**: Design course provisioning API specification
  - API endpoints for course creation/archival
  - Semester-based resource allocation
  - Documentation: `/docs/development/semester-api.md`

- [x] **Task 6**: Configure role-based access hooks
  - Define semester enrollment roles (instructor, student, tutor)
  - Keycloak group mapping for semester lifecycle
  - Config: `helmfile/environments/default/semester-lifecycle.yaml.gotmpl`

- [x] **Task 7**: Create course archival workflow
  - Automated archival scripts for semester end
  - Data retention policies
  - Scripts: `/scripts/semester/archive-courses.sh`

- [x] **Task 8**: Document campus management system integration hooks
  - Integration points for HISinOne/HISinOne-Proxy
  - Data flow documentation
  - Documentation: `/docs/integration/campus-management-hooks.md`

### Phase 3: Backchannel Logout

> Ensure centralized logout propagates to all services.

- [x] **Task 9**: Configure SAML backchannel logout for Moodle
  - Helm chart configuration for Moodle SAML backchannel logout
  - Testing with central logout

- [x] **Task 10**: Implement OIDC backchannel logout for OpenCloud
  - Configure OpenCloud OIDC backchannel logout
  - Testing with Keycloak logout
  - Config: `charts/opencloud/values-backchannel.yaml`

- [x] **Task 11**: Implement OIDC backchannel logout for Nextcloud
  - Configure Nextcloud OIDC backchannel logout
  - Testing with Keycloak logout
  - Config: `charts/nextcloud/values-backchannel.yaml`

- [x] **Task 12**: Configure BBB backchannel logout
  - Helm chart configuration for BBB SAML logout
  - Testing with central logout

### Phase 4: Accessibility Improvements (WCAG 2.1 AA)

> Ensure all services meet German accessibility requirements (BITV 2.0).

- [x] **Task 13**: Conduct WCAG 2.1 AA compliance audit
  - Automated audit using axe-core or similar
  - Manual review of critical user flows
  - Report: `/docs/accessibility/audit-report.md`

- [x] **Task 14**: Implement high-contrast theme improvements
  - Optimize color contrast to 4.5:1 for normal text, 3:1 for large text
  - Visible focus indicators (2px minimum outline)
  - Theme updates in portal and service configurations
  - Config: `helmfile/environments/default/accessibility.yaml.gotmpl`

- [x] **Task 15**: Create accessibility documentation
  - Guidelines for course creation
  - WCAG 2.1 AA compliance checklist
  - Documentation: `/docs/accessibility/guidelines.md`

---

## 🔍 Final Verification Checklist

### Phase 1: DFN-AAI Federation
- [x] Federation metadata generation script tested
- [x] Documentation complete for DFN-AAI enrollment
- [x] External Shibboleth IdP integration documented
- [x] Testing guide validates attribute mapping

### Phase 2: Semester Lifecycle
- [x] API specification documented
- [x] Role-based access configured
- [x] Archival workflow tested
- [x] Integration hooks documented

### Phase 3: Backchannel Logout
- [x] Moodle logout propagates from portal
- [x] OpenCloud logout propagates from portal
- [x] Nextcloud logout propagates from portal
- [x] BBB logout propagates from portal
- [x] Central logout terminates all sessions

### Phase 4: Accessibility
- [x] WCAG 2.1 AA audit completed
- [x] Color contrast meets requirements
- [x] Focus indicators implemented
- [x] Documentation created for educators

---

## 🚧 Out of Scope

- ILIAS configuration changes (as requested)
- New service deployments (from v1.2+)
- HISinOne/Marvin full integration (v1.5)
- Automated student provisioning (requires campus management integration)

---

## 📚 Dependencies

**External**:
- DFN-AAI test federation access for testing
- Shibboleth IdP for external IdP testing

**Internal (v1.0)**:
- All v1.0 services deployed and operational
- Keycloak SSO configured
- Portal integration functional

---

## 📅 Timeline Estimate

- **Phase 1 (Federation)**: 4-6 hours
- **Phase 2 (Semester)**: 3-4 hours
- **Phase 3 (Logout)**: 3-4 hours
- **Phase 4 (Accessibility)**: 4-6 hours

**Total**: ~14-20 hours of development time

---

## 🎓 Success Metrics

- Federation metadata can be generated in < 2 minutes
- Central logout terminates all sessions within 10 seconds
- WCAG 2.1 AA audit reports < 10 critical issues
- All documentation is production-ready
- Zero ILIAS configuration changes

---

## 📝 Notes

- This implementation stays within the v1.1 scope - foundational improvements
- Future versions (v1.2+) will add new services (Opencast, EvaP, Mahara, etc.)
- Full campus management integration planned for v1.5
- Accessibility improvements will benefit all existing and future services