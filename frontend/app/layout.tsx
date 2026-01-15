export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-50">
        <nav className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <a href="/" className="text-xl font-bold text-gray-900">
              OpsPilot
            </a>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  )
}