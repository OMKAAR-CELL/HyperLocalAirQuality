import "./globals.css";

export const metadata = {
  title: "Hyperlocal Air Quality Monitor",
  description: "Room-level CO2 and PM2.5 monitoring with outdoor comparison, forecast and chatbot",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
