import type { ReactNode } from 'react';
import { PrimaryNav } from './PrimaryNav';

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <PrimaryNav onNewAnalysis={() => undefined} />
      {children}
    </div>
  );
}
