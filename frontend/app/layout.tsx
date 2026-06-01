import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'TechNews Publisher',
  description: 'GeekNews daily summary archive',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
