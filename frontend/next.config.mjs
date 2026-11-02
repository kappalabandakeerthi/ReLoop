const appRoutes = [
  "/login",
  "/register",
  "/dashboard",
  "/devices",
  "/assessment",
  "/recommendations",
  "/providers",
  "/recovery",
  "/admin",
];

const nextConfig = {
  async rewrites() {
    return appRoutes.map((route) => ({ source: route, destination: "/" }));
  },
};

export default nextConfig;
