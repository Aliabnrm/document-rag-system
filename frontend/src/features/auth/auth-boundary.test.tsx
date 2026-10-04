import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import messages from "../../../messages/en.json";
import { loginApi, registerApi } from "@/services/api/auth/auth.api";

import { AuthBoundary } from "./auth-boundary";

vi.mock("@/services/api/auth/auth.api", () => ({
  changePasswordApi: vi.fn(),
  completeResetApi: vi.fn(),
  getCurrentUserApi: vi.fn().mockRejectedValue(new Error("unauthenticated")),
  loginApi: vi.fn(),
  logoutAllApi: vi.fn(),
  logoutApi: vi.fn(),
  registerApi: vi.fn(),
}));

function TestProviders({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return (
    <NextIntlClientProvider locale="en" messages={messages}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </NextIntlClientProvider>
  );
}

describe("AuthBoundary", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("exposes distinct login, registration, and recovery forms", async () => {
    const user = userEvent.setup();
    render(<AuthBoundary><p>Private workspace</p></AuthBoundary>, {
      wrapper: TestProviders,
    });

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeVisible();
    expect(screen.getByLabelText("Email")).toHaveAttribute("dir", "ltr");

    await user.click(screen.getByRole("button", { name: "Register" }));
    expect(screen.getByLabelText("Display name (optional)")).toBeVisible();
    expect(screen.getByLabelText("Email")).toBeVisible();
    expect(screen.getByLabelText("Password")).toHaveAttribute("minlength", "12");

    await user.click(screen.getByRole("button", { name: "Reset" }));
    expect(screen.getByLabelText("Reset token")).toBeVisible();
    expect(screen.getByLabelText("New password")).toHaveAttribute("minlength", "12");
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
  });

  it("creates an account with email and password", async () => {
    vi.mocked(registerApi).mockResolvedValue({
      id: "56f2d2e1-bc95-4637-8d47-7a21dd057afe",
      email: "new-user@example.com",
      display_name: "New User",
      idle_expires_at: "2026-09-26T09:00:00Z",
      absolute_expires_at: "2026-10-03T08:00:00Z",
    });
    const user = userEvent.setup();
    render(<AuthBoundary><p>Private workspace</p></AuthBoundary>, {
      wrapper: TestProviders,
    });

    await user.click(await screen.findByRole("button", { name: "Register" }));
    await user.type(screen.getByLabelText("Display name (optional)"), "New User");
    await user.type(screen.getByLabelText("Email"), "new-user@example.com");
    await user.type(screen.getByLabelText("Password"), "correct horse battery staple");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(registerApi).toHaveBeenCalledWith(expect.anything(), {
      displayName: "New User",
      email: "new-user@example.com",
      password: "correct horse battery staple",
    });
    expect(await screen.findByText("Private workspace")).toBeVisible();
  });

  it("submits login credentials through the auth API boundary", async () => {
    vi.mocked(loginApi).mockResolvedValue({
      id: "d8981d20-6936-4f9e-ae47-876098c8905d",
      email: "tester@example.com",
      display_name: "Tester",
      idle_expires_at: "2026-09-26T09:00:00Z",
      absolute_expires_at: "2026-10-03T08:00:00Z",
    });
    const user = userEvent.setup();
    render(<AuthBoundary><p>Private workspace</p></AuthBoundary>, {
      wrapper: TestProviders,
    });

    await user.type(await screen.findByLabelText("Email"), "tester@example.com");
    await user.type(screen.getByLabelText("Password"), "correct horse battery staple");
    const signInButtons = screen.getAllByRole("button", { name: "Sign in" });
    await user.click(signInButtons.at(-1)!);

    expect(loginApi).toHaveBeenCalledWith(expect.anything(), {
      email: "tester@example.com",
      password: "correct horse battery staple",
    });
    expect(await screen.findByText("Private workspace")).toBeVisible();
  });
});
