import { createContext, useContext, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import type { GarmentDraft } from "../types/domain";
import { createBodyProfiles } from "../features/body/measurements";
import type { BodyMode, BodyProfiles } from "../features/body/types";
import type { Auth } from "../features/garments/types";

interface SessionState {
  auth: Auth | null;
  setAuth: Dispatch<SetStateAction<Auth | null>>;
  garments: GarmentDraft[];
  setGarments: Dispatch<SetStateAction<GarmentDraft[]>>;
  bodyPhoto: File | undefined;
  setBodyPhoto: Dispatch<SetStateAction<File | undefined>>;
  clearSession: () => void;
  bodyProfiles: BodyProfiles;
  setBodyProfiles: Dispatch<SetStateAction<BodyProfiles>>;
  bodyMode: BodyMode;
  setBodyMode: Dispatch<SetStateAction<BodyMode>>;
}
const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<Auth | null>(null);
  const [garments, setGarments] = useState<GarmentDraft[]>([]);
  const [bodyPhoto, setBodyPhoto] = useState<File>();
  const [bodyProfiles, setBodyProfiles] =
    useState<BodyProfiles>(createBodyProfiles);
  const [bodyMode, setBodyMode] = useState<BodyMode>("manual");
  function clearSession() {
    setGarments([]);
    setBodyPhoto(undefined);
    setBodyProfiles(createBodyProfiles());
    setBodyMode("manual");
  }
  return (
    <SessionContext.Provider
      value={{
        auth,
        setAuth,
        garments,
        setGarments,
        bodyPhoto,
        setBodyPhoto,
        clearSession,
        bodyProfiles,
        setBodyProfiles,
        bodyMode,
        setBodyMode,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

// 기본 상태는 탭 메모리다. 별도 명시적 저장만 BodyVault에서 암호화해 처리한다.
export function useSession() {
  const session = useContext(SessionContext);
  if (!session) throw new Error("SessionProvider가 필요합니다.");
  return session;
}
