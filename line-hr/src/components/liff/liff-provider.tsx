"use client";

import type { Liff } from "@line/liff";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { AuthResponse, PublicEmployee } from "@/lib/api-types";
import { ApiError, apiFetch, errorMessage } from "@/lib/client-api";

const LIFF_ID = process.env.NEXT_PUBLIC_LIFF_ID ?? "";
const DEV_USER_KEY = "lhr_dev_user";

/** Dev mode = no LIFF ID configured. The server only accepts it with ALLOW_DEV_LOGIN=true outside production. */
export const IS_DEV_LOGIN = !LIFF_ID;

type LiffState = {
  status: "loading" | "ready" | "error";
  error: string | null;
  profile: AuthResponse["profile"] | null;
  employee: PublicEmployee | null;
  inClient: boolean;
};

type LiffContextValue = LiffState & {
  refresh: () => Promise<void>;
  closeWindow: () => void;
  devUser: string | null;
};

const LiffContext = createContext<LiffContextValue | null>(null);

let liffPromise: Promise<Liff> | null = null;

function initLiff(): Promise<Liff> {
  liffPromise ??= import("@line/liff")
    .then(async ({ default: liff }) => {
      await liff.init({ liffId: LIFF_ID, withLoginOnExternalBrowser: true });
      return liff;
    })
    .catch((err) => {
      liffPromise = null;
      throw err;
    });
  return liffPromise;
}

function storage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function devUserId(): string {
  const fromUrl = new URLSearchParams(window.location.search).get("as");
  const id = fromUrl || storage()?.getItem(DEV_USER_KEY) || "U_dev_employee";
  storage()?.setItem(DEV_USER_KEY, id);
  return id;
}

/** Returns a LINE ID token, or null when LIFF is navigating away (login redirect / liff.state redirect). */
async function getIdToken(): Promise<{ idToken: string | null; inClient: boolean }> {
  if (IS_DEV_LOGIN) return { idToken: `dev:${devUserId()}`, inClient: false };

  const liff = await initLiff();
  // Opened via https://liff.line.me/<id>/<path>: liff.init() is forwarding us to <path>.
  if (new URLSearchParams(window.location.search).has("liff.state")) return { idToken: null, inClient: false };
  if (!liff.isLoggedIn()) {
    liff.login({ redirectUri: window.location.href });
    return { idToken: null, inClient: false };
  }
  const idToken = liff.getIDToken();
  if (!idToken) throw new Error("ไม่ได้รับ ID token จาก LINE — ตรวจว่า LIFF app เปิด scope \"openid\" แล้ว");
  return { idToken, inClient: liff.isInClient() };
}

type AuthOutcome = { state: LiffState; devUser: string | null } | null;

/** Signs in and returns the new state, or null while LIFF redirects. Never touches React state itself. */
async function authenticate(): Promise<AuthOutcome> {
  try {
    const { idToken, inClient } = await getIdToken();
    if (!idToken) return null;
    const data = await apiFetch<AuthResponse>("/api/auth/line", { json: { idToken } });
    return {
      state: { status: "ready", error: null, profile: data.profile, employee: data.employee, inClient },
      devUser: IS_DEV_LOGIN ? idToken.slice(4) : null,
    };
  } catch (err) {
    if (err instanceof ApiError && err.code === "id_token_expired" && !IS_DEV_LOGIN) {
      const liff = await initLiff();
      if (!liff.isInClient()) {
        liff.logout();
        liff.login({ redirectUri: window.location.href });
        return null;
      }
    }
    const message =
      IS_DEV_LOGIN && err instanceof ApiError && err.code === "invalid_id_token"
        ? "ยังไม่ได้ตั้งค่า NEXT_PUBLIC_LIFF_ID (ถ้าทดสอบในเครื่อง ให้ตั้ง ALLOW_DEV_LOGIN=true)"
        : errorMessage(err);
    return {
      state: { status: "error", error: message, profile: null, employee: null, inClient: false },
      devUser: null,
    };
  }
}

export function LiffProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<LiffState>({
    status: "loading",
    error: null,
    profile: null,
    employee: null,
    inClient: false,
  });
  const [devUser, setDevUser] = useState<string | null>(null);

  const apply = useCallback((outcome: AuthOutcome) => {
    if (!outcome) return;
    setState(outcome.state);
    setDevUser(outcome.devUser);
  }, []);

  useEffect(() => {
    let active = true;
    void authenticate().then((outcome) => {
      if (active) apply(outcome);
    });
    return () => {
      active = false;
    };
  }, [apply]);

  const refresh = useCallback(async () => apply(await authenticate()), [apply]);

  const closeWindow = useCallback(() => {
    if (!IS_DEV_LOGIN && state.inClient) void initLiff().then((liff) => liff.closeWindow());
    else router.push("/liff");
  }, [state.inClient, router]);

  return <LiffContext value={{ ...state, refresh, closeWindow, devUser }}>{children}</LiffContext>;
}

export function useLiff(): LiffContextValue {
  const ctx = useContext(LiffContext);
  if (!ctx) throw new Error("useLiff must be used inside <LiffProvider>");
  return ctx;
}
