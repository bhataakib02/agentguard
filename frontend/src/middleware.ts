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
    request.cookies.get("sb-xjragvyzlailmtfwjfnm-auth-token")?.value ||
    supabaseCookie;

  const isPublicRoute = PUBLIC_AUTH_ROUTES.some((route) => {
    if (route === "/") {
      return pathname === "/";
    }
    return pathname === route || pathname.startsWith(`${route}/`);
  });

  // Redirect unauthenticated users accessing protected routes to the landing page '/'
  if (!token && !isPublicRoute) {
    return NextResponse.redirect(new URL("/", request.url));
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
