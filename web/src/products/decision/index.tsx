// Product 02 — Decision Assurance: nav and routes. Shared pipeline/player/brief pages mount under /decision/pipeline automatically.
import { Route } from 'react-router-dom';
import { BookOpen, LayoutDashboard, ListChecks, GitPullRequestArrow, Scale, Workflow, Upload } from 'lucide-react';
import type { ProductDef } from '../types';
import GuidePage from './GuidePage';
import DashboardPage from './DashboardPage';
import QueuePage from './QueuePage';
import CasePage from './CasePage';
import ReferralsPage from './ReferralsPage';
import SandboxPage from './SandboxPage';

export const decision: ProductDef = {
  id: 'decision', number: '02', name: 'Decision Assurance', short: 'Decisions', base: '/decision', subjectLabel: 'Case',
  tagline: 'Prepare the decision, then check the commitment',
  nav: [
    { to: '/decision/guide', label: 'Start here', icon: BookOpen },
    { to: '/decision', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/decision/cases', label: 'Case queue', icon: ListChecks },
    { to: '/decision/referrals', label: 'Referrals & assurance', icon: GitPullRequestArrow },
    { to: '/decision/rules', label: 'Rule studio', icon: Scale },
    { to: '/decision/pipeline', label: 'Pipeline & mocks', icon: Workflow },
    { to: '/decision/sandbox', label: 'Your data (real)', icon: Upload },
  ],
  routes: <>
    <Route path="decision" element={<DashboardPage />} />
    <Route path="decision/guide" element={<GuidePage />} />
    <Route path="decision/cases" element={<QueuePage />} />
    <Route path="decision/cases/:id" element={<CasePage />} />
    <Route path="decision/referrals" element={<ReferralsPage />} />
    <Route path="decision/sandbox" element={<SandboxPage />} />
  </>,
};
