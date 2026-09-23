/** Auth state. Tokens live in localStorage so a refresh doesn't sign you out. */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useAuth = create(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      email: null,
      signIn: ({ access_token, refresh_token }, email) =>
        set({ accessToken: access_token, refreshToken: refresh_token, email }),
      logout: () => set({ accessToken: null, refreshToken: null, email: null }),
    }),
    { name: "redteam-auth" },
  ),
);

export const useIsAuthed = () => useAuth((s) => Boolean(s.accessToken));
