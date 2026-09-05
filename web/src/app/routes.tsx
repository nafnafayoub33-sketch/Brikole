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
import { AuditPage } from '@/features/admin/AuditPage'
import { DashboardPage } from '@/features/admin/DashboardPage'
import { FinancePage } from '@/features/admin/FinancePage'
import { RequestsPage as AdminRequestsPage } from '@/features/admin/RequestsPage'
import { SettingsPage } from '@/features/admin/SettingsPage'
import { UsersPage } from '@/features/admin/UsersPage'
import { ChatPage as ClientChatPage } from '@/features/client/ChatPage'
import { DisputePage as ClientDisputePage } from '@/features/client/DisputePage'
import { JobPage } from '@/features/client/JobPage'
import { JobsPage } from '@/features/client/JobsPage'
import { MyDisputePage } from '@/features/client/MyDisputePage'
import { MyDisputesPage } from '@/features/client/MyDisputesPage'
import { NewRequestPage } from '@/features/client/NewRequestPage'
import { RequestPage } from '@/features/client/RequestPage'
import { RequestsPage } from '@/features/client/RequestsPage'
import { ReviewPage } from '@/features/client/ReviewPage'
import { OnboardingPage } from '@/features/pro/OnboardingPage'
import { DisputePage as ModDisputePage } from '@/features/mod/DisputePage'
import { DisputesPage } from '@/features/mod/DisputesPage'
import { ReportsPage } from '@/features/mod/ReportsPage'
import { CreditPage } from '@/features/pro/CreditPage'
import { FeedPage } from '@/features/pro/FeedPage'
import { ProJobsPage } from '@/features/pro/JobsPage'
import { MyOffersPage } from '@/features/pro/MyOffersPage'
import { ChatPage as ProChatPage } from '@/features/pro/ChatPage'
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
        <Route path="requests/:id/chats/:conversationId" element={<ClientChatPage />} />
        <Route path="requests/:id/edit" element={<NewRequestPage editing />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobPage />} />
        <Route path="jobs/:id/review" element={<ReviewPage />} />
        <Route path="jobs/:id/dispute" element={<ClientDisputePage />} />
        <Route path="disputes" element={<MyDisputesPage />} />
        <Route path="disputes/:id" element={<MyDisputePage />} />
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
        <Route path="chats/:conversationId" element={<ProChatPage />} />
        <Route path="jobs" element={<ProJobsPage />} />
        <Route path="profile" element={<NotBuilt screen="M8" />} />
        <Route path="credit" element={<CreditPage />} />
        <Route path="reviews" element={<NotBuilt screen="M10" />} />
        <Route path="disputes" element={<MyDisputesPage />} />
        <Route path="disputes/:id" element={<MyDisputePage />} />
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
        <Route path="disputes" element={<DisputesPage />} />
        <Route path="disputes/:id" element={<ModDisputePage />} />
        <Route path="reports" element={<ReportsPage />} />
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
        <Route index element={<DashboardPage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="requests" element={<AdminRequestsPage />} />
        <Route path="finance" element={<FinancePage />} />
        <Route path="catalog" element={<NotBuilt screen="A6" />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="staff" element={<NotBuilt screen="A9" />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
