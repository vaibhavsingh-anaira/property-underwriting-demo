import { Link, useParams } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { useDocument } from '@/api/client';
import { DocumentViewer } from '@/viewers/DocumentViewer';
import { Info } from '@/help/Info';

export default function DocumentPage() {
  const { id } = useParams();
  const { data: d } = useDocument(id);
  return (
    <div className="flex h-full flex-col px-6 py-4">
      <div className="mb-2 flex items-center gap-1 text-[12px] text-ink-500">
        <Link to="/documents" className="hover:text-ink-800">Documents</Link>
        {d?.account_id && <><ChevronRight className="size-3" /><Link to={`/accounts/${d.account_id}/documents`} className="hover:text-ink-800">{d.account_name}</Link></>}
        <ChevronRight className="size-3" /><span className="truncate text-ink-700">{d?.title ?? id}</span>
        <Info id="document.viewer" className="ml-1" />
      </div>
      <div className="min-h-0 flex-1 overflow-hidden rounded-[var(--radius-card)] border border-line shadow-[var(--shadow-card)]">
        {id && <DocumentViewer docId={id} height="100%" showExtraction />}
      </div>
    </div>
  );
}
