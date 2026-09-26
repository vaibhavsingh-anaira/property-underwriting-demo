// Product 01 — Renewal Integrity. Its pages live at the root (/, /renewals, /accounts/…); routes are declared in App.
import { LayoutDashboard, ListChecks, GitPullRequestArrow, Map as MapIcon, FolderOpen, Gauge, Scale, Workflow, BookOpen, Upload } from 'lucide-react';
import type { ProductDef } from './types';

export const renewal: ProductDef = {
  id: 'renewal', number: '01', name: 'Renewal Integrity', short: 'Renewals', base: '', subjectLabel: 'Account',
  tagline: 'Is the renewal what we think it is?',
  nav: [
    { to: '/guide', label: 'Start here', icon: BookOpen },
    { to: '/', label: 'Book', icon: LayoutDashboard, end: true },
    { to: '/renewals', label: 'Renewals', icon: ListChecks },
    { to: '/referrals', label: 'Referrals', icon: GitPullRequestArrow, badge: 'referrals' },
    { to: '/portfolio', label: 'Portfolio', icon: MapIcon },
    { to: '/documents', label: 'Documents', icon: FolderOpen },
    { to: '/data-quality', label: 'Data quality', icon: Gauge },
    { to: '/rules', label: 'Rule studio', icon: Scale },
    { to: '/pipeline', label: 'Pipeline & mocks', icon: Workflow },
    { to: '/sandbox', label: 'Your data (real)', icon: Upload },
  ],
  routes: <></>,
};
