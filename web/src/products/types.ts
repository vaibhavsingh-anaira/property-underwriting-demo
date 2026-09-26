import type { LucideIcon } from 'lucide-react';
import type { ReactElement } from 'react';

export type ProductId = 'renewal' | 'decision' | 'delegated';
export interface NavItem { to: string; label: string; icon: LucideIcon; end?: boolean; badge?: 'referrals' }

/** What each product contributes to the shell. Shared pages (pipeline, stage, player, brief) are mounted
 *  automatically under `${base}/pipeline…`; the product supplies its own guide, dashboard and domain pages. */
export interface ProductDef {
  id: ProductId;
  number: string;              // '01'
  name: string;                // 'Decision Assurance'
  short: string;               // 'Decisions'
  tagline: string;             // one line shown in the switcher
  base: '' | '/decision' | '/delegated';
  nav: NavItem[];              // sidebar for this product, top to bottom
  routes: ReactElement;        // <><Route path="decision/…" …/></> — paths relative to root, no leading slash
  subjectLabel: string;        // 'Account' | 'Case' | 'Coverholder'
}
