import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_AUTH_ROUTES = [
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-otp",
  "/verify-email",
  "/403",
  "/unauthorized",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  const allCookies = request.cookies.getAll();
  const supabaseCookie = allCookies.find(
    (c) =>
      c.name.startsWith("sb-") &&
      (c.name.includes("auth-token") || c.name.includes("access-token"))
  )?.value;

  const token =
    request.cookies.get("agentguard_token")?.value ||
    supabaseCookie;

  const isPublicRoute = PUBLIC_AUTH_ROUTES.some((route) => {
    if (route === "/") {
      return pathname === "/";
    }
    return pathname === route || pathname.startsWith(`${route}/`);
  });

  // Redirect unauthenticated users accessing protected routes to /login
  if (!token && !isPublicRoute) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Helper to safely parse JWT claims on the Edge runtime
  function parseJwtPayload(jwtStr: string): any {
    try {
      const parts = jwtStr.split(".");
      if (parts.length < 2) return null;
      const base64Url = parts[1];
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join("")
      );
      return JSON.parse(jsonPayload);
    } catch {
      return null;
    }
  }

  // Edge-level protection for /platform control plane routes
  if (pathname === "/platform" || pathname.startsWith("/platform/")) {
    if (!token) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
    const claims = parseJwtPayload(token);
    if (claims && claims.role && claims.role !== "SUPER_ADMIN") {
      return NextResponse.redirect(new URL("/403", request.url));
    }
  }

  // Redirect logged-in users attempting to access login/register pages to '/dashboard'
  const isGuestOnlyRoute = [
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/verify-otp",
    "/verify-email",
  ].some((route) => pathname === route || pathname.startsWith(`${route}/`));

  if (token && isGuestOnlyRoute) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
