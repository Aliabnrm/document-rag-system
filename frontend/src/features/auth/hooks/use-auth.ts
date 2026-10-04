"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  ChangePasswordInput,
  CompleteResetInput,
  LoginInput,
  RegistrationInput,
} from "@/schema/auth/auth.schema";
import {
  changePasswordApi,
  completeResetApi,
  getCurrentUserApi,
  loginApi,
  logoutAllApi,
  logoutApi,
  registerApi,
} from "@/services/api/auth/auth.api";
import { coreApi } from "@/services/api/core-api";

const authKey = ["auth", "current-user"] as const;

export function useAuth() {
  const queryClient = useQueryClient();
  const currentUser = useQuery({
    queryKey: authKey,
    queryFn: ({ signal }) => getCurrentUserApi(coreApi, signal),
    retry: false,
  });
  const acceptUser = async (user: Awaited<ReturnType<typeof loginApi>>) => {
    queryClient.setQueryData(authKey, user);
    await queryClient.invalidateQueries({ queryKey: ["document-qa"] });
  };
  const clearUser = () => {
    queryClient.setQueryData(authKey, null);
    queryClient.removeQueries({ queryKey: ["document-qa"] });
  };

  const login = useMutation({
    mutationFn: (input: LoginInput) => loginApi(coreApi, input),
    onSuccess: acceptUser,
  });
  const register = useMutation({
    mutationFn: (input: RegistrationInput) => registerApi(coreApi, input),
    onSuccess: acceptUser,
  });
  const logout = useMutation({
    mutationFn: () => logoutApi(coreApi),
    onSuccess: clearUser,
  });
  const logoutAll = useMutation({
    mutationFn: () => logoutAllApi(coreApi),
    onSuccess: clearUser,
  });
  const changePassword = useMutation({
    mutationFn: (input: ChangePasswordInput) => changePasswordApi(coreApi, input),
  });
  const completeReset = useMutation({
    mutationFn: (input: CompleteResetInput) => completeResetApi(coreApi, input),
  });

  return {
    user: currentUser.data ?? null,
    isLoading: currentUser.isPending,
    isAuthenticated: Boolean(currentUser.data),
    login,
    register,
    logout,
    logoutAll,
    changePassword,
    completeReset,
  };
}
