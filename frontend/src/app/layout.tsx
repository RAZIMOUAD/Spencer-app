import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/layout/Navbar';
import Sidebar from '@/components/layout/Sidebar';

export const metadata: Metadata = {
  title: 'Spencer — Stabilité des Talus',
  description:
    "Analyse de stabilité des pentes par méthode de Spencer (Eurocode 7 / EN 1997-1)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="flex flex-col h-screen overflow-hidden">
        <Navbar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-auto bg-[var(--color-bg-page)] p-5">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
