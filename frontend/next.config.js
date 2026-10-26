/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // NEXT_PUBLIC_API_URL=/api ile tarayıcı API'ye arayüzün kendi adresinden ulaşır; böylece yalnızca
  // 3000 portu yeterli olur ve aynı Wi-Fi'deki telefon da http://<bilgisayar-ip>:3000 ile açabilir.
  async rewrites() {
    const target = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: target + "/api/:path*" }];
  },
};
module.exports = nextConfig;
