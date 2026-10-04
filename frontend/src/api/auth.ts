import { isR, pick, str, toUser } from './normalize';
import { request } from './client';
import type { User } from '../types';

export async function login(email: string, password: string): Promise<string> {
  const res = await request('/api/auth/login', { method: 'POST', json: { email, password }, auth: false });
  const token = isR(res) ? str(pick(res, 'access_token', 'token')) : undefined;
  if (!token) throw new Error('Login response did not include an access token');
  return token;
}
export async function register(p: { full_name: string; email: string; organization: string; password: string }): Promise<void> {
  await request('/api/auth/register', { method: 'POST', json: p, auth: false });
}
export async function me(): Promise<User> {
  const res = await request('/api/auth/me');
  return toUser(isR(res) ? (isR(res.user) ? res.user : res) : {});
}
