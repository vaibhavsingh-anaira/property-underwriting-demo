// Plain text / YAML viewer with line numbers and light syntax tint.
import { useMemo, type ReactNode } from 'react';
import { cssSize } from './util';

export interface TextViewerProps { text: string; language?: 'yaml' | 'txt' | 'json' | string; height?: number | string; highlightLines?: number[] }

const SCALAR = /^(\s*)(-\s+)?([^\s#:][^#:]*?)(\s*:)(\s|$)/;

function tintValue(v: string, key: string | number): ReactNode {
  const t = v.trim();
  if (!t) return v;
  let cls = 'text-ink-800';
  if (/^(["']).*\1$/.test(t)) cls = 'text-[#1f7a4c]';
  else if (/^-?\d[\d_,.]*(e-?\d+)?%?$/i.test(t)) cls = 'text-info';
  else if (/^(true|false|null|~|yes|no)$/i.test(t)) cls = 'text-obs-n';
  else if (/^[>|][+-]?$/.test(t)) cls = 'text-ink-400';
  return <span key={key} className={cls}>{v}</span>;
}

function yamlLine(line: string): ReactNode {
  const hash = line.search(/(^|\s)#/);
  const code = hash >= 0 ? line.slice(0, hash) : line;
  const comment = hash >= 0 ? line.slice(hash) : '';
  const out: ReactNode[] = [];
  const m = SCALAR.exec(code);
  if (m) {
    out.push(m[1]);
    if (m[2]) out.push(<span key="d" className="text-ink-400">{m[2]}</span>);
    out.push(<span key="k" className="text-accent-700">{m[3]}</span>, <span key="c" className="text-ink-400">{m[4]}</span>);
    out.push(tintValue(code.slice(m[0].length - m[5].length), 'v'));
  } else {
    const d = /^(\s*)(-\s+)(.*)$/.exec(code);
    if (d) out.push(d[1], <span key="d" className="text-ink-400">{d[2]}</span>, tintValue(d[3], 'v'));
    else out.push(code);
  }
  if (comment) out.push(<span key="cm" className="italic text-ink-400">{comment}</span>);
  return out;
}

export function TextViewer({ text, language = 'txt', height, highlightLines }: TextViewerProps) {
  const lines = useMemo(() => text.replace(/\r\n/g, '\n').replace(/\n$/, '').split('\n'), [text]);
  const hl = new Set(highlightLines ?? []);
  const yaml = language === 'yaml' || language === 'yml';
  const gutter = String(lines.length).length;
  return (
    <div className="overflow-auto bg-surface" style={{ height: cssSize(height, 'auto') }}>
      <table className="mono w-full border-collapse text-[12px] leading-[20px]">
        <tbody>
          {lines.map((l, i) => (
            <tr key={i} className={hl.has(i + 1) ? 'bg-accent-50' : 'hover:bg-ink-50'}>
              <td className="sticky left-0 select-none border-r border-line bg-ink-50 pl-3 pr-2.5 text-right align-top text-ink-400" style={{ width: `${gutter + 3}ch` }}>{i + 1}</td>
              <td className="whitespace-pre pl-3 pr-4 text-ink-800">{yaml ? yamlLine(l) : l || ' '}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
