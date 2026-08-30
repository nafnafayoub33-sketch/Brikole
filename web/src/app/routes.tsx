import { Navigate, Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/app/layouts/AppLayout'
import { PublicLayout } from '@/app/layouts/PublicLayout'
import { ADMIN_NAV, CLIENT_NAV, MOD_NAV, PRO_NAV } from '@/app/nav'
import { RequireRole } from '@/app/RequireRole'
import { ForgotPage } from '@/features/auth/ForgotPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { RegisterPage } from '@/features/auth/RegisterPage'
import { BrowsePage } from '@/features/public/BrowsePage'
import { ApprovalsPage } from '@/features/admin/ApprovalsPage'
import { JobPage } from '@/features/client/JobPage'
import { JobsPage } from '@/features/client/JobsPage'
import { NewRequestPage } from '@/features/client/NewRequestPage'
import { RequestPage } from '@/features/client/RequestPage'
import { RequestsPage } from '@/features/client/RequestsPage'
import { ReviewPage } from '@/features/client/ReviewPage'
import { OnboardingPage } from '@/features/pro/OnboardingPage'
import { FeedPage } from '@/features/pro/FeedPage'
import { ProJobsPage } from '@/features/pro/JobsPage'
import { MyOffersPage } from '@/features/pro/MyOffersPage'
import { OfferPage } from '@/features/pro/OfferPage'
import { ProHome } from '@/features/pro/ProHome'
import { StatusPage } from '@/features/pro/StatusPage'
import { LandingPage } from '@/features/public/LandingPage'
import { ProviderProfilePage } from '@/features/public/ProviderProfilePage'
import { NotFoundPage } from '@/features/public/NotFoundPage'
import { NotBuilt } from '@/ui/NotBuilt'

/**
 * Every route in docs/SCREENS.md, gated by role.
 *
 * Screens that are not built yet render a placeholder naming their id rather
 * than being absent — a 404 on a route the spec promises is indistinguishable
 * from a bug.
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<LandingPage />} />
        <Route path="services" element={<BrowsePage />} />
        <Route path="services/:slug" element={<BrowsePage />} />
        {/* Public profile lives under /m3allem, not /pro: /pro is the
            tradesman's own area and /pro/:id would fight /pro/requests. */}
        <Route path="m3allem/:id" element={<ProviderProfilePage />} />
      </Route>

      {/* Outside PublicLayout on purpose: AuthLayout is a full-screen frame
          with its own header, and nesting the two showed two logos. */}
      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
      <Route path="forgot" element={<ForgotPage />} />

      <Route
        path="client"
        element={
          <RequireRole allow={['client']}>
            <AppLayout items={CLIENT_NAV} />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="requests" replace />} />
        <Route path="requests" element={<RequestsPage />} />
        <Route path="requests/new" element={<NewRequestPage />} />
        <Route path="requests/:id" element={<RequestPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobPage />} />
        <Route path="jobs/:id/review" element={<ReviewPage />} />
        <Route path="jobs/:id/dispute" element={<NotBuilt screen="C8" />} />
        <Route path="notifications" element={<NotBuilt screen="C6" />} />
        <Route path="account" element={<NotBuilt screen="C7" />} />
      </Route>

      <Route
        path="pro"
        element={
          <RequireRole allow={['provider']}>
            <AppLayout items={PRO_NAV} />
          </RequireRole>
        }
      >
        <Route index element={<ProHome />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route path="status" element={<StatusPage />} />
        <Route path="requests" element={<FeedPage />} />
        <Route path="requests/:id" element={<OfferPage />} />
        <Route path="offers" element={<MyOffersPage />} />
        <Route path="jobs" element={<ProJobsPage />} />
        <Route path="profile" element={<NotBuilt screen="M8" />} />
        <Route path="credit" element={<NotBuilt screen="M9" />} />
        <Route path="reviews" element={<NotBuilt screen="M10" />} />
        <Route path="account" element={<NotBuilt screen="M11" />} />
      </Route>

      {/* An admin can do everything a moderator can, so he is allowed here
          too — the permission table says so, and the routes follow it. */}
      <Route
        path="mod"
        element={
          <RequireRole allow={['moderator', 'admin']}>
            <AppLayout items={MOD_NAV} />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="disputes" replace />} />
        <Route path="disputes" element={<NotBuilt screen="D1" />} />
        <Route path="disputes/:id" element={<NotBuilt screen="D2" />} />
        <Route path="reports" element={<NotBuilt screen="D3" />} />
        <Route path="account" element={<NotBuilt screen="D4" />} />
      </Route>

      <Route
        path="admin"
        element={
          <RequireRole allow={['admin']}>
            <AppLayout items={ADMIN_NAV} />
          </RequireRole>
        }
      >
        <Route index element={<NotBuilt screen="A1" />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="users" element={<NotBuilt screen="A3" />} />
        <Route path="requests" element={<NotBuilt screen="A4" />} />
        <Route path="finance" element={<NotBuilt screen="A5" />} />
        <Route path="catalog" element={<NotBuilt screen="A6" />} />
        <Route path="settings" element={<NotBuilt screen="A7" />} />
        <Route path="audit" element={<NotBuilt screen="A8" />} />
        <Route path="staff" element={<NotBuilt screen="A9" />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
