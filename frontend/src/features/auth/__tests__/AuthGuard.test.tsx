import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthGuard } from "../components/AuthGuard";
import * as authStore from "@/api/auth-store";
import * as auth from "@/api/auth";

beforeEach(() => {
  authStore.clearAccessToken();
});

function renderGuard(initialRoute = "/") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route element={<AuthGuard />}>
          <Route path="/" element={<div>Protected Content</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AuthGuard", () => {
  it("renders children when access token exists", () => {
    authStore.setAccessToken("valid-token");
    renderGuard();
    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("attempts silent refresh when no token and shows content on success", async () => {
    vi.spyOn(auth, "refreshApi").mockResolvedValueOnce({
      access_token: "restored-token",
      token_type: "bearer",
    });

    renderGuard();

    // Should show loading initially, then protected content
    expect(await screen.findByText("Protected Content")).toBeInTheDocument();
    expect(authStore.getAccessToken()).toBe("restored-token");
  });

  it("redirects to /login when refresh fails", async () => {
    vi.spyOn(auth, "refreshApi").mockRejectedValueOnce(
      new auth.RefreshError(401),
    );

    renderGuard();

    expect(await screen.findByText("Login Page")).toBeInTheDocument();
  });

  it("redirects to /login on network error during refresh", async () => {
    vi.spyOn(auth, "refreshApi").mockRejectedValueOnce(
      new Error("Network error"),
    );

    renderGuard();

    expect(await screen.findByText("Login Page")).toBeInTheDocument();
  });
});
