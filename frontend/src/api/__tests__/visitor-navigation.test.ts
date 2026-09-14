import { expect, it, vi } from 'vitest';
import { AxiosError } from 'axios';
const session = vi.hoisted(() => ({isAuthenticated:false,accessToken:null,refreshAccessToken:vi.fn(),logout:vi.fn()}));
vi.mock('@/store/auth',()=>({useAuthStore:{getState:()=>session},isImpersonating:()=>false}));
vi.mock('react-hot-toast',()=>({default:{error:vi.fn()}}));
import { api } from '../axios';
it('leaves a visitor on the current page when private content requires sign-in',async()=>{
  const oldLocation=window.location.href;
  api.defaults.adapter=async config=>{throw new AxiosError('Sign in required','ERR_BAD_REQUEST',config,undefined,{status:401,statusText:'Unauthorized',data:{detail:'Sign in'},headers:{},config})};
  await expect(api.get('/virtual-labs/private-investigation')).rejects.toMatchObject({response:{status:401}});
  expect(session.refreshAccessToken).not.toHaveBeenCalled();
  expect(session.logout).not.toHaveBeenCalled();
  expect(window.location.href).toBe(oldLocation);
});
