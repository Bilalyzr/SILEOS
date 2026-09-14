import { useEffect } from "react";
import { useAuthStore } from "@/store/auth";
import { syncOffline } from "./learning";

/** Resume pending device work after sign-in or returning to the online LMS. */
export function OfflineSyncBridge() {
  const userId = useAuthStore((state) => state.user?.id);
  useEffect(() => {
    if (!userId) return;
    const sync = () => {
      void syncOffline().catch(() => {
        /* Device storage may be disabled. The reader exposes retry status. */
      });
    };
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("focus", sync);
    };
  }, [userId]);
  return null;
}
