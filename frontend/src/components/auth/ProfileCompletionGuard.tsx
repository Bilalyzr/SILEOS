import { useEffect } from 'react';
import { useAuthStore } from '@/store/auth';
import { MobileNumberGate } from '@/components/auth/MobileNumberGate';

interface ProfileCompletionGuardProps {
  children: React.ReactNode;
}

/**
 * Route guard that redirects users to profile page if profile is not completed
 * Only applies to authenticated users who haven't completed their profile
 */
export const ProfileCompletionGuard = ({ children }: ProfileCompletionGuardProps) => {
  const { user, isAuthenticated } = useAuthStore();

  useEffect(() => {
    // Skip guard if not authenticated
    if (!isAuthenticated || !user) {
      return;
    }

    // Profile completion guard disabled - users can freely navigate
    // They will see a banner on profile page to complete their profile
  }, [user, isAuthenticated]);

  // Students with no mobile number on file (Google accounts created before the
  // number was mandatory) get a blocking prompt over whatever page they land on.
  return (
    <>
      {children}
      <MobileNumberGate />
    </>
  );
};
