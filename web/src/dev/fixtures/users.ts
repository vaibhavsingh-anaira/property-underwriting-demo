import type { User } from '@/api/types';

export const USERS: User[] = [
  { user_id: 'u_maya', name: 'Maya Chen', role: 'UNDERWRITER', authority_level: 1, title: 'Underwriter', initials: 'MC' },
  { user_id: 'u_daniel', name: 'Daniel Okafor', role: 'UNDERWRITER', authority_level: 2, title: 'Underwriter', initials: 'DO' },
  { user_id: 'u_tom', name: 'Tom Brennan', role: 'UNDERWRITER', authority_level: 3, title: 'Lead Underwriter', initials: 'TB' },
  { user_id: 'u_aisha', name: 'Aisha Patel', role: 'UNDERWRITER', authority_level: 2, title: 'Underwriter', initials: 'AP' },
  { user_id: 'u_priya', name: 'Priya Raman', role: 'SENIOR_UNDERWRITER', authority_level: 3, title: 'Senior Underwriter', initials: 'PR' },
  { user_id: 'u_robert', name: 'Robert Hale', role: 'CUO', authority_level: 4, title: 'Chief Underwriting Officer', initials: 'RH' },
  { user_id: 'u_elena', name: 'Elena Brooks', role: 'RISK_ENGINEER', authority_level: 1, title: 'Risk Engineer', initials: 'EB' },
];
export const UW_IDS = ['u_maya', 'u_daniel', 'u_tom', 'u_aisha'] as const;
export const userName = (id: string) => USERS.find((u) => u.user_id === id)?.name ?? id;
