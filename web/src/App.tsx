import { Route, Routes } from 'react-router-dom';
import { Shell } from '@/layout/Shell';
import BookPage from '@/pages/BookPage';
import RenewalsPage from '@/pages/RenewalsPage';
import AccountPage from '@/pages/account/AccountPage';
import ReferralsPage from '@/pages/ReferralsPage';
import PortfolioPage from '@/pages/PortfolioPage';
import DocumentsPage from '@/pages/DocumentsPage';
import DocumentPage from '@/pages/DocumentPage';
import DataQualityPage from '@/pages/DataQualityPage';
import RulesPage from '@/pages/RulesPage';
import RulePage from '@/pages/RulePage';
import PipelinePage from '@/pages/PipelinePage';
import StagePage from '@/pages/pipeline/StagePage';
import JourneyPage from '@/pages/pipeline/JourneyPage';
import ViewerGallery from '@/viewers/ViewerGallery';
import GuidePage from '@/pages/GuidePage';
import SandboxPage from '@/pages/SandboxPage';
import BriefPage from '@/pages/pipeline/BriefPage';
import { decision } from '@/products/decision';
import { delegated } from '@/products/delegated';

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<BookPage />} />
        <Route path="renewals" element={<RenewalsPage />} />
        <Route path="accounts/:id" element={<AccountPage />} />
        <Route path="accounts/:id/:tab" element={<AccountPage />} />
        <Route path="referrals" element={<ReferralsPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="documents/:id" element={<DocumentPage />} />
        <Route path="data-quality" element={<DataQualityPage />} />
        <Route path="rules" element={<RulesPage />} />
        <Route path="rules/:id" element={<RulePage />} />
        <Route path="pipeline" element={<PipelinePage />} />
        <Route path="pipeline/journey" element={<JourneyPage />} />
        <Route path="pipeline/brief/:pid" element={<BriefPage />} />
        <Route path="guide" element={<GuidePage />} />
        <Route path="sandbox" element={<SandboxPage />} />
        <Route path="pipeline/:code" element={<StagePage />} />
        <Route path="_viewers" element={<ViewerGallery />} />
        {/* shared pipeline, stage, player and brief pages for the other two products */}
        <Route path="decision/rules" element={<RulesPage />} />
        {['decision', 'delegated'].map((p) => [
          <Route key={p + 'pl'} path={`${p}/pipeline`} element={<PipelinePage />} />,
          <Route key={p + 'j'} path={`${p}/pipeline/journey`} element={<JourneyPage />} />,
          <Route key={p + 'b'} path={`${p}/pipeline/brief/:pid`} element={<BriefPage />} />,
          <Route key={p + 's'} path={`${p}/pipeline/:code`} element={<StagePage />} />,
          <Route key={p + 'r'} path={`${p}/rules/:id`} element={<RulePage />} />,
        ])}
        {decision.routes}
        {delegated.routes}
      </Route>
    </Routes>
  );
}
