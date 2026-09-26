// Product registry: the shell, the shared pipeline/player pages and the guide all read from here.
import { useLocation } from 'react-router-dom';
import { renewal } from './renewal';
import { decision } from './decision';
import { delegated } from './delegated';
import type { ProductDef, ProductId } from './types';

export type { ProductDef, ProductId } from './types';
export const PRODUCTS: ProductDef[] = [renewal, decision, delegated];
export const productById = (id: string | undefined): ProductDef => PRODUCTS.find((p) => p.id === id) ?? renewal;

export function productOfPath(pathname: string): ProductDef {
  return PRODUCTS.find((p) => p.base && (pathname === p.base || pathname.startsWith(p.base + '/'))) ?? renewal;
}

/** The product the current route belongs to, plus a helper to build links inside it. */
export function useProduct(): ProductDef & { id: ProductId; to: (path: string) => string } {
  const { pathname } = useLocation();
  const p = productOfPath(pathname);
  return { ...p, to: (path: string) => (p.base + (path.startsWith('/') ? path : '/' + path)).replace(/\/$/, '') || '/' };
}
