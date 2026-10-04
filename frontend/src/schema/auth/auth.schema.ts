import { z } from "zod";

export const CurrentUserSchema = z.object({
  id: z.string().uuid(),
  email: z.string(),
  display_name: z.string().nullable(),
  idle_expires_at: z.iso.datetime(),
  absolute_expires_at: z.iso.datetime(),
});

export type CurrentUser = z.infer<typeof CurrentUserSchema>;

export type LoginInput = {
  email: string;
  password: string;
};

export type RegistrationInput = LoginInput & {
  displayName?: string;
};

export type ChangePasswordInput = {
  currentPassword: string;
  newPassword: string;
};

export type CompleteResetInput = {
  token: string;
  newPassword: string;
};
