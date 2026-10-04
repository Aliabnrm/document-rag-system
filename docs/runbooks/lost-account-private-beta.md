# Operator-assisted lost-account recovery

There is no automated email/SMS recovery in Sprint 2. This avoids an unaccepted provider cost,
regional-access dependency, and account-enumeration endpoint.

1. Verify the tester through the pre-agreed private channel.
2. Run `create-password-reset --email … --expires-in 30m`.
3. Send the one-time secret through that channel; do not retain a copy.
4. The user enters the token and a new password in the bilingual reset screen.
5. Successful consumption changes the Argon2id hash, marks the token used, and revokes all sessions
   in one transaction.
6. Ask the user to sign in again. Reusing the token must fail.

If ownership cannot be verified, do not reset the account. MFA, WebAuthn, verified-email delivery,
and recovery codes are future security decisions, not hidden Sprint 2 behavior.
