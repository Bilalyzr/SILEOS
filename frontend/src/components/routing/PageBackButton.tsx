import { ArrowLeft } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import { safeBackFallback } from './page-guides';

export function usePageBack() {
  const location=useLocation(), navigate=useNavigate();
  const role=useAuthStore(s=>s.user?.role);
  return () => {
    if(typeof window.history.state?.idx==='number' && window.history.state.idx>0){navigate(-1);return;}
    try {
      const ref=new URL(document.referrer);
      if(ref.origin===window.location.origin && ref.pathname!==location.pathname){navigate(ref.pathname+ref.search+ref.hash,{replace:true});return;}
    } catch { /* Direct entry uses the parent destination. */ }
    navigate(safeBackFallback(location.pathname,role),{replace:true});
  };
}

export function PageBackButton({className='astra-back-button'}:{className?:string}) {
  const back=usePageBack();
  return <button type="button" className={className} onClick={back} aria-label="Go back to previous page"><ArrowLeft size={17}/>Back</button>;
}
