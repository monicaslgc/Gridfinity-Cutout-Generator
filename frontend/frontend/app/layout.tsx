export const metadata = {
  title: "Gridfinity Cutout Generator",
  description: "Generate Gridfinity containers and preview STL files",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <div className="max-w-6xl mx-auto p-6">
          <header className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-semibold">Gridfinity Cutout Generator</h1>
            <a className="text-sm opacity-75 hover:opacity-100 underline" href="https://github.com/monicaslgc/Gridfinity-Cutout-Generator" target="_blank" rel="noreferrer">GitHub</a>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
