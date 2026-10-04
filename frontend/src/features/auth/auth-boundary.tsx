"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, type ReactNode, useState } from "react";

import { Button } from "@/components/ui/button";
import { errorCodeOf } from "@/services/api/api-error";

import { useAuth } from "./hooks/use-auth";
import styles from "./auth.module.css";

type AuthMode = "login" | "register" | "reset";

export function AuthBoundary({ children }: { children: ReactNode }) {
  const t = useTranslations("Auth");
  const auth = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");

  if (auth.isLoading) {
    return <p className={styles.loading} role="status">{t("checkingSession")}</p>;
  }

  if (!auth.isAuthenticated || !auth.user) {
    const activeMutation = mode === "login"
      ? auth.login
      : mode === "register"
        ? auth.register
        : auth.completeReset;
    const error = activeMutation.error
      ? authErrorMessage(errorCodeOf(activeMutation.error), t)
      : null;

    function selectMode(nextMode: AuthMode) {
      auth.login.reset();
      auth.register.reset();
      auth.completeReset.reset();
      setMode(nextMode);
    }

    async function submit(event: FormEvent<HTMLFormElement>) {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      if (mode === "login") {
        await auth.login.mutateAsync({
          email: String(form.get("email")),
          password: String(form.get("password")),
        }).catch(() => undefined);
      } else if (mode === "register") {
        await auth.register.mutateAsync({
          email: String(form.get("email")),
          password: String(form.get("password")),
          displayName: String(form.get("displayName") ?? ""),
        }).catch(() => undefined);
      } else {
        await auth.completeReset.mutateAsync({
          token: String(form.get("resetToken")),
          newPassword: String(form.get("newPassword")),
        }).then(() => selectMode("login")).catch(() => undefined);
      }
    }

    return (
      <section className={styles.authPanel} aria-labelledby="auth-title">
        <div className={styles.authCopy}>
          <p className={styles.kicker}>{t("privateBeta")}</p>
          <h2 id="auth-title">{t(`${mode}Title`)}</h2>
          <p>{t(`${mode}Description`)}</p>
        </div>
        <div className={styles.authFormColumn}>
          <div className={styles.modeSwitch} role="group" aria-label={t("modeLabel")}>
            {(["login", "register", "reset"] as const).map((item) => (
              <button
                className={mode === item ? styles.modeActive : styles.modeButton}
                type="button"
                key={item}
                aria-pressed={mode === item}
                onClick={() => selectMode(item)}
              >
                {t(`${item}Tab`)}
              </button>
            ))}
          </div>
          <form className={styles.form} onSubmit={(event) => void submit(event)}>
            {mode === "register" ? (
              <Field label={t("displayName")} name="displayName" autoComplete="name" required={false} />
            ) : null}
            {mode !== "reset" ? (
              <Field label={t("email")} name="email" type="email" autoComplete="email" direction="ltr" />
            ) : (
              <Field label={t("resetToken")} name="resetToken" autoComplete="off" />
            )}
            <Field
              label={mode === "reset" ? t("newPassword") : t("password")}
              name={mode === "reset" ? "newPassword" : "password"}
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={12}
            />
            {error ? <p className={styles.error} role="alert">{error}</p> : null}
            {mode === "reset" && auth.completeReset.isSuccess ? (
              <p className={styles.success} role="status">{t("resetCompleted")}</p>
            ) : null}
            <Button type="submit" disabled={activeMutation.isPending}>
              {activeMutation.isPending ? t("submitting") : t(`${mode}Action`)}
            </Button>
          </form>
        </div>
      </section>
    );
  }

  return (
    <>
      <section className={styles.accountBar} aria-label={t("accountLabel")}>
        <div>
          <strong>{auth.user.display_name || auth.user.email}</strong>
          {auth.user.display_name ? <span dir="ltr">{auth.user.email}</span> : null}
        </div>
        <div className={styles.accountActions}>
          <details className={styles.securityDetails}>
            <summary>{t("securitySettings")}</summary>
            <PasswordChangeForm
              error={auth.changePassword.error ? authErrorMessage(errorCodeOf(auth.changePassword.error), t) : null}
              isPending={auth.changePassword.isPending}
              isSuccess={auth.changePassword.isSuccess}
              onSubmit={(currentPassword, newPassword) =>
                auth.changePassword.mutate({ currentPassword, newPassword })
              }
            />
            <Button
              variant="danger"
              size="compact"
              disabled={auth.logoutAll.isPending}
              onClick={() => auth.logoutAll.mutate()}
            >
              {t("logoutAll")}
            </Button>
          </details>
          <Button
            variant="secondary"
            size="compact"
            disabled={auth.logout.isPending}
            onClick={() => auth.logout.mutate()}
          >
            {t("logout")}
          </Button>
        </div>
      </section>
      {children}
    </>
  );
}

type FieldProps = {
  label: string;
  name: string;
  type?: "email" | "password" | "text";
  autoComplete: string;
  direction?: "ltr";
  required?: boolean;
  minLength?: number;
};

function Field({ label, name, type = "text", autoComplete, direction, required = true, minLength }: FieldProps) {
  return (
    <label className={styles.field}>
      <span>{label}</span>
      <input
        name={name}
        type={type}
        autoComplete={autoComplete}
        dir={direction}
        required={required}
        minLength={minLength}
      />
    </label>
  );
}

function PasswordChangeForm({
  error,
  isPending,
  isSuccess,
  onSubmit,
}: {
  error: string | null;
  isPending: boolean;
  isSuccess: boolean;
  onSubmit: (currentPassword: string, newPassword: string) => void;
}) {
  const t = useTranslations("Auth");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSubmit(String(form.get("currentPassword")), String(form.get("newPassword")));
  }
  return (
    <form className={styles.securityForm} onSubmit={submit}>
      <Field label={t("currentPassword")} name="currentPassword" type="password" autoComplete="current-password" />
      <Field label={t("newPassword")} name="newPassword" type="password" autoComplete="new-password" minLength={12} />
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      {isSuccess ? <p className={styles.success} role="status">{t("passwordChanged")}</p> : null}
      <Button size="compact" type="submit" disabled={isPending}>{t("changePassword")}</Button>
    </form>
  );
}

function authErrorMessage(code: string, t: ReturnType<typeof useTranslations>): string {
  const keyByCode: Record<string, string> = {
    invalid_credentials: "invalidCredentials",
    registration_unavailable: "registrationUnavailable",
    password_too_short: "passwordTooShort",
    password_too_long: "passwordTooLong",
    password_too_common: "passwordTooCommon",
    invalid_password_reset: "invalidReset",
    rate_limited: "rateLimited",
    network_error: "serviceUnavailable",
  };
  return t(keyByCode[code] ?? "genericError");
}
