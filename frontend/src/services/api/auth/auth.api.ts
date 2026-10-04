import type { AxiosInstance } from "axios";

import {
  CurrentUserSchema,
  type ChangePasswordInput,
  type CompleteResetInput,
  type CurrentUser,
  type LoginInput,
  type RegistrationInput,
} from "@/schema/auth/auth.schema";
import { requestAndParse } from "@/services/api/core-api";

export function getCurrentUserApi(
  api: AxiosInstance,
  signal?: AbortSignal,
): Promise<CurrentUser> {
  return requestAndParse(api.get("/api/v1/auth/me", { signal }), CurrentUserSchema);
}

export function loginApi(api: AxiosInstance, input: LoginInput): Promise<CurrentUser> {
  return requestAndParse(
    api.post("/api/v1/auth/sessions", input),
    CurrentUserSchema,
  );
}

export function registerApi(
  api: AxiosInstance,
  input: RegistrationInput,
): Promise<CurrentUser> {
  return requestAndParse(
    api.post("/api/v1/auth/registrations", {
      email: input.email,
      password: input.password,
      display_name: input.displayName || null,
    }),
    CurrentUserSchema,
  );
}

export async function logoutApi(api: AxiosInstance): Promise<void> {
  await api.delete("/api/v1/auth/session");
}

export async function logoutAllApi(api: AxiosInstance): Promise<void> {
  await api.delete("/api/v1/auth/sessions");
}

export async function changePasswordApi(
  api: AxiosInstance,
  input: ChangePasswordInput,
): Promise<void> {
  await api.post("/api/v1/auth/password-changes", {
    current_password: input.currentPassword,
    new_password: input.newPassword,
  });
}

export async function completeResetApi(
  api: AxiosInstance,
  input: CompleteResetInput,
): Promise<void> {
  await api.post("/api/v1/auth/password-resets/complete", {
    token: input.token,
    new_password: input.newPassword,
  });
}
