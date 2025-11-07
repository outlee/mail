# Authentication & Authorization System

## Overview

The MTBF Platform implements a JWT-based authentication system with role-based access control (RBAC). All authentication is handled via access tokens and refresh tokens with Argon2 password hashing.

## Architecture

### User Roles

The system supports three user roles:

- **Maintainer**: Full platform access, can register new users, manage system settings
- **Operator**: Can perform operational tasks and view dashboards
- **Manager**: Can view reports and manage team resources

### Token Management

#### Access Token
- **Type**: JWT Bearer token
- **Default Expiry**: 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Claims**: 
  - `sub`: User ID
  - `role`: User role
  - `exp`: Expiration timestamp

#### Refresh Token
- **Type**: JWT Bearer token with `type: refresh` claim
- **Default Expiry**: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- **Claims**:
  - `sub`: User ID
  - `role`: User role
  - `type`: "refresh"
  - `exp`: Expiration timestamp
- **Storage**: Hashed in database with revocation support
- **Rotation**: New refresh token issued on each refresh operation

### Password Hashing

Passwords are hashed using **Argon2** with the following features:
- Salted hashing (salt included in hash)
- Memory-hard algorithm resistant to GPU/ASIC attacks
- Configurable time/memory cost factors

## API Endpoints

### POST `/auth/login`

Authenticate user with email and password.

**Parameters:**
```
email: string (required, query)
password: string (required, query)
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Status Codes:**
- `200 OK`: Successful login
- `401 Unauthorized`: Invalid credentials

---

### POST `/auth/refresh`

Refresh access token using a valid refresh token.

**Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Status Codes:**
- `200 OK`: Token refreshed successfully
- `401 Unauthorized`: Invalid or expired refresh token

---

### POST `/auth/register`

Register a new user (maintainer only).

**Headers:**
```
Authorization: Bearer {access_token}
```

**Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "operator",
  "is_active": true
}
```

**Status Codes:**
- `201 Created`: User created successfully
- `400 Bad Request`: Email already registered or invalid input
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: User is not a maintainer

---

### GET `/auth/me`

Get current authenticated user information.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "operator",
  "is_active": true
}
```

**Status Codes:**
- `200 OK`: User information retrieved
- `401 Unauthorized`: Missing or invalid token

---

### POST `/auth/logout`

Logout current user (clears session on frontend).

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

**Status Codes:**
- `200 OK`: Logout successful
- `401 Unauthorized`: Missing or invalid token

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token",
  "headers": {
    "WWW-Authenticate": "Bearer"
  }
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

## Environment Variables

Add the following to your `.env` file:

```env
# JWT Configuration
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Important**: In production, use a strong, randomly generated `JWT_SECRET` (minimum 32 characters).

## Frontend Integration

### Session Storage

- Access tokens are stored in `sessionStorage` (cleared on browser close)
- Refresh tokens are stored in `sessionStorage` for session persistence

### Token Refresh Flow

1. Request made with access token
2. If 401 response received:
   - Attempt to refresh with refresh token
   - Update both tokens in storage
   - Retry original request
   - If refresh fails, redirect to login

### Protected Routes

Use the `ProtectedRoute` component to restrict access:

```tsx
<Route
  path="/dashboard"
  element={
    <ProtectedRoute requiredRoles={['operator', 'maintainer']}>
      <Dashboard />
    </ProtectedRoute>
  }
/>
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id VARCHAR(36) PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  role ENUM('maintainer', 'operator', 'manager') DEFAULT 'operator',
  is_active CHAR(1) DEFAULT '1',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Refresh Tokens Table
```sql
CREATE TABLE refresh_tokens (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  token_hash VARCHAR(255) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  revoked CHAR(1) DEFAULT '0',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Security Best Practices

1. **Always use HTTPS** in production
2. **Use strong JWT_SECRET**: Generate with `openssl rand -base64 32`
3. **Token Expiry**: Short access token expiry (15 min) with longer refresh token expiry
4. **CORS**: Configure `CORS_ORIGINS` to trusted domains only
5. **Password Policy**: Enforce strong passwords (min 8 characters in production)
6. **Refresh Token Rotation**: New refresh token issued on each refresh
7. **Token Revocation**: Refresh tokens can be revoked via database

## Testing

### Unit Tests
Run authentication tests with:
```bash
pytest tests/test_auth.py -v
```

### Playwright Tests
Run end-to-end tests with:
```bash
playwright test tests/auth.spec.ts
```

## Future Enhancements

- [ ] Support for SSO (SAML/OIDC)
- [ ] Multi-factor authentication (MFA)
- [ ] SCIM provisioning
- [ ] Audit logging for auth events
- [ ] Password reset flows
- [ ] Account lockout after failed attempts
- [ ] OAuth2/OpenID Connect integration
