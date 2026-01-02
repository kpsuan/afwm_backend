# RBAC and Data Masking Implementation

## Overview

This document describes the Role-Based Access Control (RBAC) and data masking implementation for sensitive user data in the AWFM platform.

## Sensitive Data Fields

The following fields are considered sensitive and have special handling:
- `phone_number` - User's phone number
- `birth_date` - User's date of birth
- `location` - User's location/city

## Access Levels

### Superusers (Admin/Founder)
- **Access**: Full access to all data (unmasked)
- **Permissions**: Can view and edit all fields
- **Use Case**: Platform administrators, founders

### Staff Users (Future Customer Support/Operations)
- **Access**: Limited access with data masking
- **Permissions**:
  - Can view: email, name, display_name, bio, pronouns, HCW status
  - **Cannot view**: phone_number, birth_date, location (fields are hidden)
  - Cannot edit sensitive fields (read-only if visible)
- **Use Case**: Customer support, operations team

## Data Masking Strategies

### Phone Number Masking
- **Full**: `(555) 123-4567`
- **Masked**: `***-4567` (shows last 4 digits only)
- Implementation: `_mask_phone()` method in `admin.py`

### Birth Date Masking
- **Full**: `1990-05-15`
- **Masked**: `1990-**-**` (shows year only)
- Implementation: `_mask_birth_date()` method in `admin.py`

### Location
- **Full**: `San Francisco, CA`
- **Masked**: Hidden completely (not shown to staff)

## Audit Logging

All access to user detail pages is logged with:
- Who accessed (email of admin user)
- Which user was viewed (email and ID)
- When it was accessed (timestamp)
- From where (IP address)

Logs are written to: `accounts.admin` logger

Example log entry:
```
INFO: User detail accessed: admin@example.com viewed user john@example.com (ID: abc-123) | IP: 192.168.1.1
```

## Implementation Details

### Admin List View
- Superusers see full phone numbers
- Staff see masked phone numbers (`***-4567`)

### Admin Detail View
- **Superusers**: All fields visible and editable
- **Staff**: Sensitive fields hidden via `get_fieldsets()`

### Readonly Fields
- Non-superusers cannot edit: `phone_number`, `birth_date`, `location`, `email`
- Always readonly: `created_at`, `updated_at`, `last_login_at`, `hcw_attested_at`

## Future Enhancements

When hiring staff, consider:

1. **Custom Groups**
   ```python
   # Create groups in Django admin
   - "Customer Support" - basic access
   - "Senior Support" - can see masked sensitive data
   - "Operations Manager" - can see some unmasked data
   ```

2. **Field-Level Permissions**
   - Use Django Guardian or similar for object-level permissions
   - Implement temporary access grants for specific cases

3. **Dynamic Data Masking**
   - Implement real-time masking at database level
   - Use database views or triggers for automatic masking

4. **Two-Factor Authentication**
   - Require 2FA for accessing sensitive data
   - Implement step-up authentication for viewing PII

5. **Access Request System**
   - Staff can request temporary access to unmasked data
   - Requires manager approval
   - Auto-expires after time limit

## Compliance Notes

This implementation helps meet:
- **HIPAA**: Access control and audit logging for PHI
- **GDPR**: Data minimization and access restrictions
- **CCPA**: Privacy protections for California residents

## Testing RBAC

To test the masking system:

1. Create a test staff user:
```python
python manage.py createsuperuser --email staff@test.com
# Set is_superuser=False, is_staff=True in admin
```

2. Log in as staff user and verify:
   - Phone numbers are masked in list view
   - Sensitive fields are hidden in detail view
   - Access is logged

3. Log in as superuser and verify:
   - All data is visible
   - All fields are editable

## Code References

- **Admin Config**: `/apps/accounts/admin.py`
- **User Model**: `/apps/accounts/models.py`
- **Logging Config**: `/config/settings/base.py` (add logger configuration)

## Questions or Issues?

Contact: [Your Email/Team Lead]
