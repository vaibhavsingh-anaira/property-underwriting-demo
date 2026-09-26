// Product 03 — Delegated Authority Control: nav and routes (shared pipeline/player/brief pages are mounted by App).
import { Route } from 'react-router-dom';
import { BookOpen, LayoutDashboard, Building2, ShieldAlert, FileSpreadsheet, Map as MapIcon, Scale, Workflow, Upload } from 'lucide-react';
import type { ProductDef } from '../types';
import Guide from './pages/Guide';
import Dashboard from './pages/Dashboard';
import Coverholders from './pages/Coverholders';
import Coverholder from './pages/Coverholder';
import Breaches from './pages/Breaches';
import Bordereaux from './pages/Bordereaux';
import Aggregates from './pages/Aggregates';
import Rules from './pages/Rules';
import Sandbox from './pages/Sandbox';

export const delegated: ProductDef = {
  id: 'delegated', number: '03', name: 'Delegated Authority', short: 'Delegated', base: '/delegated', subjectLabel: 'Coverholder',
  tagline: 'Is the coverholder writing what we authorised?',
  nav: [
    { to: '/delegated/guide', label: 'Start here', icon: BookOpen },
    { to: '/delegated', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/delegated/coverholders', label: 'Coverholders', icon: Building2 },
    { to: '/delegated/breaches', label: 'Breach register', icon: ShieldAlert },
    { to: '/delegated/bordereaux', label: 'Bordereaux', icon: FileSpreadsheet },
    { to: '/delegated/aggregates', label: 'Aggregates', icon: MapIcon },
    { to: '/delegated/rules', label: 'Rule studio', icon: Scale },
    { to: '/delegated/pipeline', label: 'Pipeline & mocks', icon: Workflow },
    { to: '/delegated/sandbox', label: 'Your data (real)', icon: Upload },
  ],
  routes: (
    <>
      <Route path="delegated" element={<Dashboard />} />
      <Route path="delegated/guide" element={<Guide />} />
      <Route path="delegated/coverholders" element={<Coverholders />} />
      <Route path="delegated/coverholders/:id" element={<Coverholder />} />
      <Route path="delegated/breaches" element={<Breaches />} />
      <Route path="delegated/bordereaux" element={<Bordereaux />} />
      <Route path="delegated/aggregates" element={<Aggregates />} />
      <Route path="delegated/rules" element={<Rules />} />
      <Route path="delegated/sandbox" element={<Sandbox />} />
    </>
  ),
};
