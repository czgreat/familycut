import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { AuthResponse, MemberProfile, fetchCurrentMember, loginMember } from "./api";

type AuthSession = {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
};

type AuthContextValue = {
  session: AuthSession | null;
  member: MemberProfile | null;
  booting: boolean;
  login: (username: string, password: string) => Promise<AuthResponse>;
  acceptAuth: (payload: AuthResponse) => void;
  logout: () => void;
  updateMember: (member: MemberProfile) => void;
};

const storageKey = "familycut_mobile_session";

const AuthContext = createContext<AuthContextValue | null>(null);

function readSession(): AuthSession | null {
  const raw = window.localStorage.getItem(storageKey);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    window.localStorage.removeItem(storageKey);
    return null;
  }
}

function persistSession(session: AuthSession | null): void {
  if (session) {
    window.localStorage.setItem(storageKey, JSON.stringify(session));
    return;
  }
  window.localStorage.removeItem(storageKey);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => readSession());
  const [member, setMember] = useState<MemberProfile | null>(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function hydrateMember() {
      if (!session?.accessToken) {
        setMember(null);
        setBooting(false);
        return;
      }

      setBooting(true);
      try {
        const currentMember = await fetchCurrentMember(session.accessToken);
        if (!cancelled) {
          setMember(currentMember);
        }
      } catch {
        if (!cancelled) {
          persistSession(null);
          setSession(null);
          setMember(null);
        }
      } finally {
        if (!cancelled) {
          setBooting(false);
        }
      }
    }

    void hydrateMember();

    return () => {
      cancelled = true;
    };
  }, [session]);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      member,
      booting,
      async login(username: string, password: string) {
        const payload = await loginMember(username, password);
        const nextSession = {
          accessToken: payload.tokens.access_token,
          refreshToken: payload.tokens.refresh_token,
          tokenType: payload.tokens.token_type
        };
        persistSession(nextSession);
        setSession(nextSession);
        return payload;
      },
      acceptAuth(payload: AuthResponse) {
        const nextSession = {
          accessToken: payload.tokens.access_token,
          refreshToken: payload.tokens.refresh_token,
          tokenType: payload.tokens.token_type
        };
        persistSession(nextSession);
        setSession(nextSession);
      },
      logout() {
        persistSession(null);
        setSession(null);
        setMember(null);
      },
      updateMember(nextMember: MemberProfile) {
        setMember(nextMember);
      }
    }),
    [booting, member, session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth 必须在 AuthProvider 内使用。");
  }
  return context;
}

export function isProfileComplete(member: MemberProfile | null): boolean {
  if (!member) {
    return false;
  }
  return Boolean(member.display_name && member.sex && member.birth_year && member.height_cm);
}
