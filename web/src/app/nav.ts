import type { NavItem } from '@/app/layouts/AppLayout'

/** The menus from docs/SCREENS.md, one list per role. */

export const CLIENT_NAV: NavItem[] = [
  { to: '/client/requests/new', labelKey: 'nav.newRequest' },
  // The client reaches C9 from a request, so the count rides here.
  { to: '/client/requests', labelKey: 'nav.myRequests', end: true, chats: true },
  { to: '/client/jobs', labelKey: 'nav.myJobsNav', end: true },
  { to: '/client/notifications', labelKey: 'nav.notifications' },
  { to: '/client/account', labelKey: 'nav.account' },
]

export const PRO_NAV: NavItem[] = [
  { to: '/pro', labelKey: 'nav.dashboard', end: true },
  { to: '/pro/requests', labelKey: 'nav.requests' },
  // And the tradesman reaches M12 from his offers.
  { to: '/pro/offers', labelKey: 'nav.myOffers', chats: true },
  { to: '/pro/jobs', labelKey: 'nav.myJobs' },
  { to: '/pro/credit', labelKey: 'nav.credit' },
  { to: '/pro/account', labelKey: 'nav.account' },
]

export const MOD_NAV: NavItem[] = [
  { to: '/mod/disputes', labelKey: 'nav.disputes' },
  { to: '/mod/reports', labelKey: 'nav.reports' },
  { to: '/mod/account', labelKey: 'nav.account' },
]

export const ADMIN_NAV: NavItem[] = [
  { to: '/admin', labelKey: 'nav.dashboard', end: true },
  { to: '/admin/approvals', labelKey: 'nav.approvals' },
  { to: '/admin/users', labelKey: 'nav.users' },
  { to: '/admin/finance', labelKey: 'nav.finance' },
  { to: '/admin/catalog', labelKey: 'nav.catalog' },
  { to: '/admin/settings', labelKey: 'nav.settings' },
  { to: '/admin/audit', labelKey: 'nav.audit' },
]
