# Security Policy

## Supported Versions

Currently supported versions for security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of Email Agent seriously. If you discover a security vulnerability, please follow these steps:

1. **DO NOT** create a public GitHub issue
2. Email your findings to security@haas.holdings
3. Include the following in your report:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: We'll acknowledge receipt within 48 hours
- **Initial Assessment**: Within 7 days, we'll provide an initial assessment
- **Resolution Timeline**: We'll work with you to understand and resolve the issue
- **Disclosure**: Once fixed, we'll coordinate disclosure with you

### Security Best Practices for Users

1. **API Keys**: 
   - Never commit API keys to version control
   - Use environment variables or secure key management
   - Rotate keys regularly

2. **Gmail OAuth**:
   - Only use official OAuth flows
   - Review granted permissions carefully
   - Revoke access for unused installations

3. **Database**:
   - Ensure database files are properly secured
   - Use encryption for sensitive data
   - Regular backups with secure storage

4. **Docker**:
   - Keep base images updated
   - Don't run containers as root
   - Use secrets management for credentials

## Security Features

Email Agent includes several security features:

- OAuth 2.0 for Gmail authentication
- Encrypted storage for sensitive configuration
- Secure credential management via keyring
- Sandboxed agent execution
- Rate limiting for API calls

## Acknowledgments

We appreciate responsible disclosure and will acknowledge security researchers who help improve Email Agent's security.