import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname === "/") {
    return NextResponse.rewrite(new URL("/console", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/"]
};
