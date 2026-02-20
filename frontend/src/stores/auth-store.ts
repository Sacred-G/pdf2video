import { create } from "zustand";

type AuthState = {
  token: string | null;
  email: string | null;
  setAuth: (payload: { token: string; email: string }) => void;
  clear: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  email: null,
  setAuth: ({ token, email }) => set({ token, email }),
  clear: () => set({ token: null, email: null })
}));
